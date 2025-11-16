/**
 * WebSocketInputService - WebSocket communication for VNC input event transmission
 *
 * Handles:
 * - WebSocket connection management with noVNC server
 * - Input event serialization and compression
 * - Message acknowledgment and reliability
 * - Input batching for bandwidth optimization
 * - Connection recovery and error handling
 * - Latency monitoring and optimization
 */

import { EventEmitter } from 'events';
import RFB from '@novnc/novnc/lib/rfb.js';

export interface WebSocketConfig {
  url: string;
  protocols?: string[];
  reconnectAttempts: number;
  reconnectDelay: number;
  timeout: number;
  enableCompression: boolean;
  batchSize: number;
  batchTimeout: number;
  enableLatencyMonitoring: boolean;
}

export interface InputMessage {
  id: string;
  type: 'mouse' | 'keyboard' | 'touch' | 'focus';
  data: any;
  timestamp: number;
  priority: 'low' | 'normal' | 'high' | 'urgent';
}

export interface ConnectionMetrics {
  connectedAt: number;
  lastPingTime: number;
  roundTripTime: number;
  messagesSent: number;
  messagesReceived: number;
  messagesAcked: number;
  errors: number;
  reconnections: number;
}

export class WebSocketInputService extends EventEmitter {
  private config: WebSocketConfig;
  private websocket: WebSocket | null = null;
  private rfb: RFB | null = null;
  private isConnected = false;
  private isConnecting = false;

  // Message handling
  private messageQueue: InputMessage[] = [];
  private pendingAcks: Map<string, number> = new Map();
  private messageId = 0;
  private batchTimer: number | null = null;

  // Performance metrics
  private metrics: ConnectionMetrics;
  private latencyHistory: number[] = [];
  private maxLatencyHistory = 100;

  // Connection state
  private reconnectAttempts = 0;
  private reconnectTimeout: number | null = null;
  private pingInterval: number | null = null;

  constructor(config: Partial<WebSocketConfig> = {}) {
    super();

    this.config = {
      url: 'ws://localhost:6080',
      protocols: ['binary'],
      reconnectAttempts: 5,
      reconnectDelay: 2000,
      timeout: 10000,
      enableCompression: true,
      batchSize: 10,
      batchTimeout: 16, // ~60fps
      enableLatencyMonitoring: true,
      ...config
    };

    this.metrics = {
      connectedAt: 0,
      lastPingTime: 0,
      roundTripTime: 0,
      messagesSent: 0,
      messagesReceived: 0,
      messagesAcked: 0,
      errors: 0,
      reconnections: 0
    };
  }

  /**
   * Connect to WebSocket server
   */
  public async connect(url?: string): Promise<void> {
    if (this.isConnected || this.isConnecting) {
      return;
    }

    const connectUrl = url || this.config.url;
    this.isConnecting = true;

    try {
      this.websocket = new WebSocket(connectUrl, this.config.protocols);
      this.setupWebSocketHandlers();

      await this.waitForConnection();

      // Initialize RFB connection if available
      if (typeof RFB !== 'undefined') {
        this.initializeRFB(connectUrl);
      }

      this.isConnected = true;
      this.isConnecting = false;
      this.reconnectAttempts = 0;
      this.metrics.connectedAt = Date.now();

      // Start monitoring
      this.startPingInterval();
      this.startBatchProcessing();

      this.emit('connected');
      console.log('WebSocket connected to:', connectUrl);

    } catch (error) {
      this.isConnecting = false;
      this.handleError(error as Error);
      throw error;
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  public disconnect(): void {
    this.clearReconnectTimeout();
    this.clearPingInterval();
    this.clearBatchTimer();

    if (this.websocket) {
      this.websocket.close();
      this.websocket = null;
    }

    if (this.rfb) {
      this.rfb.disconnect();
      this.rfb = null;
    }

    this.isConnected = false;
    this.isConnecting = false;
    this.messageQueue = [];

    this.emit('disconnected');
  }

  /**
   * Check if connected
   */
  public isConnectedState(): boolean {
    return this.isConnected && this.websocket?.readyState === WebSocket.OPEN;
  }

  /**
   * Send mouse event
   */
  public async sendMouseEvent(mouseEvent: any): Promise<void> {
    const message: InputMessage = {
      id: this.generateMessageId(),
      type: 'mouse',
      data: mouseEvent,
      timestamp: Date.now(),
      priority: mouseEvent.type === 'click' ? 'high' : 'normal'
    };

    await this.sendMessage(message);
  }

  /**
   * Send keyboard event
   */
  public async sendKeyboardEvent(keyboardEvent: any): Promise<void> {
    const message: InputMessage = {
      id: this.generateMessageId(),
      type: 'keyboard',
      data: keyboardEvent,
      timestamp: Date.now(),
      priority: keyboardEvent.type === 'keydown' ? 'high' : 'normal'
    };

    await this.sendMessage(message);
  }

  /**
   * Send touch event
   */
  public async sendTouchEvent(touchEvent: any): Promise<void> {
    const message: InputMessage = {
      id: this.generateMessageId(),
      type: 'touch',
      data: touchEvent,
      timestamp: Date.now(),
      priority: 'normal'
    };

    await this.sendMessage(message);
  }

  /**
   * Send focus event
   */
  public async sendFocusEvent(focusEvent: any): Promise<void> {
    const message: InputMessage = {
      id: this.generateMessageId(),
      type: 'focus',
      data: focusEvent,
      timestamp: Date.now(),
      priority: 'high'
    };

    await this.sendMessage(message);
  }

  /**
   * Send message with batching and priority handling
   */
  private async sendMessage(message: InputMessage): Promise<void> {
    if (!this.isConnectedState()) {
      // Queue message for when connection is restored
      this.messageQueue.push(message);
      return;
    }

    // High priority messages are sent immediately
    if (message.priority === 'urgent' || message.priority === 'high') {
      await this.sendSingleMessage(message);
    } else {
      // Lower priority messages are batched
      this.messageQueue.push(message);

      if (this.messageQueue.length >= this.config.batchSize) {
        await this.processBatch();
      }
    }
  }

  /**
   * Send single message immediately
   */
  private async sendSingleMessage(message: InputMessage): Promise<void> {
    try {
      const serializedMessage = this.serializeMessage(message);
      const compressedData = this.config.enableCompression
        ? this.compressData(serializedMessage)
        : serializedMessage;

      if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
        this.websocket.send(compressedData);
        this.metrics.messagesSent++;

        // Track for acknowledgment
        if (this.config.enableLatencyMonitoring) {
          this.pendingAcks.set(message.id, Date.now());
        }
      }
    } catch (error) {
      this.handleError(error as Error);
    }
  }

  /**
   * Process message batch
   */
  private async processBatch(): Promise<void> {
    if (this.messageQueue.length === 0) return;

    const batch = this.messageQueue.splice(0, this.config.batchSize);
    const batchMessage = {
      type: 'batch',
      messages: batch,
      timestamp: Date.now()
    };

    try {
      const serializedMessage = this.serializeMessage(batchMessage);
      const compressedData = this.config.enableCompression
        ? this.compressData(serializedMessage)
        : serializedMessage;

      if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
        this.websocket.send(compressedData);
        this.metrics.messagesSent += batch.length;

        // Track batch messages
        if (this.config.enableLatencyMonitoring) {
          batch.forEach(msg => {
            this.pendingAcks.set(msg.id, Date.now());
          });
        }
      }
    } catch (error) {
      this.handleError(error as Error);
      // Re-queue failed messages
      this.messageQueue.unshift(...batch);
    }
  }

  /**
   * Start batch processing timer
   */
  private startBatchProcessing(): void {
    this.batchTimer = window.setInterval(async () => {
      if (this.messageQueue.length > 0) {
        await this.processBatch();
      }
    }, this.config.batchTimeout);
  }

  private clearBatchTimer(): void {
    if (this.batchTimer) {
      clearInterval(this.batchTimer);
      this.batchTimer = null;
    }
  }

  /**
   * Serialize message for transmission
   */
  private serializeMessage(message: any): ArrayBuffer {
    // Create a binary message format
    const jsonString = JSON.stringify(message);
    const encoder = new TextEncoder();
    return encoder.encode(jsonString).buffer;
  }

  /**
   * Compress data (placeholder - would use actual compression)
   */
  private compressData(data: ArrayBuffer): ArrayBuffer {
    // This is a placeholder for actual compression implementation
    // Could use gzip, deflate, or custom compression for input events
    return data;
  }

  /**
   * Setup WebSocket event handlers
   */
  private setupWebSocketHandlers(): void {
    if (!this.websocket) return;

    this.websocket.onopen = this.handleOpen;
    this.websocket.onclose = this.handleClose;
    this.websocket.onerror = this.handleErrorEvent;
    this.websocket.onmessage = this.handleMessage;
  }

  private handleOpen = (): void => {
    console.log('WebSocket connection opened');
  };

  private handleClose = (event: CloseEvent): void => {
    console.log('WebSocket connection closed:', event.code, event.reason);
    this.isConnected = false;

    // Handle reconnection
    if (event.code !== 1000 && this.reconnectAttempts < this.config.reconnectAttempts) {
      this.scheduleReconnect();
    }

    this.emit('disconnected', { code: event.code, reason: event.reason });
  };

  private handleErrorEvent = (error: Event): void => {
    console.error('WebSocket error:', error);
    this.metrics.errors++;
    this.emit('error', error);
  };

  private handleMessage = (event: MessageEvent): void => {
    this.metrics.messagesReceived++;

    try {
      const data = event.data;
      const message = this.deserializeMessage(data);

      // Handle acknowledgment messages
      if (message.type === 'ack') {
        this.handleAcknowledgment(message.messageId);
      } else if (message.type === 'ping') {
        this.handlePing();
      } else {
        this.emit('message', message);
      }
    } catch (error) {
      console.error('Error handling WebSocket message:', error);
    }
  };

  private deserializeMessage(data: ArrayBuffer): any {
    const decoder = new TextDecoder();
    const jsonString = decoder.decode(data);
    return JSON.parse(jsonString);
  }

  private handleAcknowledgment(messageId: string): void {
    const sentTime = this.pendingAcks.get(messageId);
    if (sentTime) {
      const latency = Date.now() - sentTime;
      this.updateLatencyMetrics(latency);
      this.pendingAcks.delete(messageId);
      this.metrics.messagesAcked++;
    }
  }

  private handlePing(): void {
    // Respond to server ping
    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      const pongMessage = { type: 'pong', timestamp: Date.now() };
      const serializedData = this.serializeMessage(pongMessage);
      this.websocket.send(serializedData);
    }
  }

  /**
   * Initialize RFB connection for VNC protocol
   */
  private initializeRFB(url: string): void {
    try {
      // This would initialize the actual noVNC RFB connection
      // For now, we'll use the WebSocket directly
      console.log('RFB initialization would happen here with URL:', url);
    } catch (error) {
      console.error('Failed to initialize RFB:', error);
    }
  }

  /**
   * Latency monitoring
   */
  private updateLatencyMetrics(latency: number): void {
    this.latencyHistory.push(latency);
    if (this.latencyHistory.length > this.maxLatencyHistory) {
      this.latencyHistory.shift();
    }

    // Update average round-trip time
    this.metrics.roundTripTime = this.latencyHistory.reduce((sum, l) => sum + l, 0) / this.latencyHistory.length;

    // Emit high latency warning
    if (latency > 500) {
      this.emit('highLatency', latency);
    }
  }

  /**
   * Connection management
   */
  private waitForConnection(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.websocket) {
        reject(new Error('WebSocket not initialized'));
        return;
      }

      const timeout = setTimeout(() => {
        reject(new Error('Connection timeout'));
      }, this.config.timeout);

      const onOpen = () => {
        clearTimeout(timeout);
        resolve();
      };

      const onError = (error: Event) => {
        clearTimeout(timeout);
        reject(new Error('Connection failed'));
      };

      this.websocket!.addEventListener('open', onOpen, { once: true });
      this.websocket!.addEventListener('error', onError, { once: true });
    });
  }

  private scheduleReconnect(): void {
    this.reconnectAttempts++;
    this.metrics.reconnections++;

    const delay = this.config.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    this.reconnectTimeout = window.setTimeout(async () => {
      try {
        console.log(`Attempting reconnection (${this.reconnectAttempts}/${this.config.reconnectAttempts})`);
        await this.connect();
      } catch (error) {
        console.error('Reconnection failed:', error);
      }
    }, delay);
  }

  private clearReconnectTimeout(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
  }

  /**
   * Ping interval for connection health monitoring
   */
  private startPingInterval(): void {
    this.pingInterval = window.setInterval(() => {
      if (this.isConnectedState()) {
        this.metrics.lastPingTime = Date.now();
        const pingMessage = { type: 'ping', timestamp: this.metrics.lastPingTime };
        const serializedData = this.serializeMessage(pingMessage);
        this.websocket!.send(serializedData);
      }
    }, 30000); // Ping every 30 seconds
  }

  private clearPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  /**
   * Utility methods
   */
  private generateMessageId(): string {
    return `msg_${Date.now()}_${++this.messageId}`;
  }

  private handleError(error: Error): void {
    this.metrics.errors++;
    this.emit('error', error);
    console.error('WebSocketInputService error:', error);
  }

  /**
   * Get connection metrics
   */
  public getMetrics(): ConnectionMetrics & {
    isConnected: boolean;
    averageLatency: number;
    pendingAcks: number;
    queuedMessages: number;
  } {
    return {
      ...this.metrics,
      isConnected: this.isConnectedState(),
      averageLatency: this.metrics.roundTripTime,
      pendingAcks: this.pendingAcks.size,
      queuedMessages: this.messageQueue.length
    };
  }

  /**
   * Reset metrics
   */
  public resetMetrics(): void {
    this.metrics = {
      connectedAt: this.isConnected ? this.metrics.connectedAt : 0,
      lastPingTime: this.metrics.lastPingTime,
      roundTripTime: 0,
      messagesSent: 0,
      messagesReceived: 0,
      messagesAcked: 0,
      errors: 0,
      reconnections: 0
    };
    this.latencyHistory = [];
    this.pendingAcks.clear();
  }

  /**
   * Update configuration
   */
  public updateConfig(newConfig: Partial<WebSocketConfig>): void {
    this.config = { ...this.config, ...newConfig };
  }

  /**
   * Process queued messages after reconnection
   */
  public async processQueuedMessages(): Promise<void> {
    while (this.messageQueue.length > 0 && this.isConnectedState()) {
      await this.processBatch();
      // Small delay to prevent overwhelming the connection
      await new Promise(resolve => setTimeout(resolve, 10));
    }
  }

  /**
   * Cleanup resources
   */
  public destroy(): void {
    this.disconnect();
    this.removeAllListeners();
    this.latencyHistory = [];
    this.pendingAcks.clear();
  }
}

export default WebSocketInputService;