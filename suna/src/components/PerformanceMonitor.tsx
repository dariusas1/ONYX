'use client';

import React, { useEffect, useRef } from 'react';

interface PerformanceMetrics {
  loadTime: number;
  firstContentfulPaint: number;
  largestContentfulPaint: number;
  cumulativeLayoutShift: number;
  firstInputDelay: number;
}

interface PerformanceMonitorProps {
  onMetricsUpdate?: (metrics: PerformanceMetrics) => void;
  children?: React.ReactNode;
}

export function PerformanceMonitor({ onMetricsUpdate, children }: PerformanceMonitorProps) {
  const metricsRef = useRef<Partial<PerformanceMetrics>>({});
  const observerRef = useRef<PerformanceObserver>();

  useEffect(() => {
    // Only run in browser
    if (typeof window === 'undefined') return;

    const updateMetrics = () => {
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      const loadTime = navigation.loadEventEnd - navigation.fetchStart;

      const metrics: PerformanceMetrics = {
        loadTime,
        firstContentfulPaint: metricsRef.current.firstContentfulPaint || 0,
        largestContentfulPaint: metricsRef.current.largestContentfulPaint || 0,
        cumulativeLayoutShift: metricsRef.current.cumulativeLayoutShift || 0,
        firstInputDelay: metricsRef.current.firstInputDelay || 0,
      };

      onMetricsUpdate?.(metrics);

      // Log to console for debugging
      console.log('Performance Metrics:', metrics);

      // Store in session storage for analytics
      try {
        sessionStorage.setItem('performance-metrics', JSON.stringify(metrics));
      } catch (error) {
        console.warn('Failed to store performance metrics:', error);
      }
    };

    // Measure page load time
    const measurePageLoad = () => {
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      const loadTime = navigation.loadEventEnd - navigation.fetchStart;
      metricsRef.current.loadTime = loadTime;

      console.log(`Page load time: ${loadTime}ms`);

      // Check if we meet the <2s target
      if (loadTime > 2000) {
        console.warn(`Page load time exceeds 2s target: ${loadTime}ms`);
      }
    };

    // Observe Core Web Vitals
    const observeWebVitals = () => {
      // First Contentful Paint
      try {
        const fcpObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (entry.name === 'first-contentful-paint') {
              metricsRef.current.firstContentfulPaint = entry.startTime;
              console.log(`First Contentful Paint: ${entry.startTime.toFixed(2)}ms`);
            }
          }
        });
        fcpObserver.observe({ type: 'paint', buffered: true });
      } catch (error) {
        console.warn('FCP observer not supported:', error);
      }

      // Largest Contentful Paint
      try {
        const lcpObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            metricsRef.current.largestContentfulPaint = entry.startTime;
            console.log(`Largest Contentful Paint: ${entry.startTime.toFixed(2)}ms`);
          }
        });
        lcpObserver.observe({ type: 'largest-contentful-paint', buffered: true });
      } catch (error) {
        console.warn('LCP observer not supported:', error);
      }

      // Cumulative Layout Shift
      try {
        let clsValue = 0;
        const clsObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (!(entry as any).hadRecentInput) {
              clsValue += (entry as any).value;
              metricsRef.current.cumulativeLayoutShift = clsValue;
            }
          }
          console.log(`Cumulative Layout Shift: ${clsValue.toFixed(4)}`);
        });
        clsObserver.observe({ type: 'layout-shift', buffered: true });
      } catch (error) {
        console.warn('CLS observer not supported:', error);
      }

      // First Input Delay
      try {
        const fidObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (entry.entryType === 'first-input') {
              metricsRef.current.firstInputDelay = (entry as any).processingStart - entry.startTime;
              console.log(`First Input Delay: ${metricsRef.current.firstInputDelay.toFixed(2)}ms`);
            }
          }
        });
        fidObserver.observe({ type: 'first-input', buffered: true });
      } catch (error) {
        console.warn('FID observer not supported:', error);
      }
    };

    // Initialize measurements
    if (document.readyState === 'complete') {
      measurePageLoad();
    } else {
      window.addEventListener('load', measurePageLoad);
    }

    observeWebVitals();

    // Final metrics update after page loads
    setTimeout(updateMetrics, 100);

    return () => {
      window.removeEventListener('load', measurePageLoad);
    };
  }, [onMetricsUpdate]);

  return <>{children}</>;
}

export function getStoredMetrics(): PerformanceMetrics | null {
  if (typeof window === 'undefined') return null;

  try {
    const stored = sessionStorage.getItem('performance-metrics');
    return stored ? JSON.parse(stored) : null;
  } catch (error) {
    console.warn('Failed to retrieve performance metrics:', error);
    return null;
  }
}