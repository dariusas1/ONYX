-- Migration 003: Message Citations System
-- Story 2-6: Response Citation & Source Attribution

-- Create message_citations table to store citation links between messages and source documents
CREATE TABLE IF NOT EXISTS message_citations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    citation_index INTEGER NOT NULL, -- [1], [2], [3] in the text
    snippet TEXT, -- Relevant text snippet from the document
    confidence_score FLOAT DEFAULT 1.0 CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    citation_metadata JSONB DEFAULT '{}', -- Additional metadata like source type, date, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Ensure unique citation numbers per message
    UNIQUE(message_id, citation_index)
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_message_citations_message_id ON message_citations(message_id);
CREATE INDEX IF NOT EXISTS idx_message_citations_document_id ON message_citations(document_id);
CREATE INDEX IF NOT EXISTS idx_message_citations_citation_index ON message_citations(citation_index);
CREATE INDEX IF NOT EXISTS idx_message_citations_confidence ON message_citations(confidence_score);
CREATE INDEX IF NOT EXISTS idx_message_citations_created_at ON message_citations(created_at);

-- Add citations JSONB column to messages table for inline citation storage
ALTER TABLE messages
ADD COLUMN IF NOT EXISTS citations JSONB DEFAULT '{}';

-- Create index for message citations JSONB field
CREATE INDEX IF NOT EXISTS idx_messages_citations_gin ON messages USING GIN(citations);

-- Add RLS (Row Level Security) policies for message_citations
ALTER TABLE message_citations ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view citations for messages they have access to
CREATE POLICY "Users can view accessible message citations" ON message_citations
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM messages
            WHERE messages.id = message_citations.message_id
            AND messages.user_id = auth.uid()
        )
    );

-- Policy: Users can insert citations for their own messages
CREATE POLICY "Users can insert citations for own messages" ON message_citations
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM messages
            WHERE messages.id = message_citations.message_id
            AND messages.user_id = auth.uid()
        )
    );

-- Policy: Users can update citations for their own messages
CREATE POLICY "Users can update citations for own messages" ON message_citations
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM messages
            WHERE messages.id = message_citations.message_id
            AND messages.user_id = auth.uid()
        )
    );

-- Policy: Users can delete citations for their own messages
CREATE POLICY "Users can delete citations for own messages" ON message_citations
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM messages
            WHERE messages.id = message_citations.message_id
            AND messages.user_id = auth.uid()
        )
    );

-- Create function to clean up orphaned citations
CREATE OR REPLACE FUNCTION cleanup_orphaned_citations()
RETURNS void AS $$
BEGIN
    DELETE FROM message_citations
    WHERE message_id NOT IN (SELECT id FROM messages)
    OR (document_id IS NOT NULL AND document_id NOT IN (SELECT id FROM documents));
END;
$$ LANGUAGE plpgsql;

-- Create function to extract citation statistics
CREATE OR REPLACE FUNCTION get_citation_stats(p_message_id UUID)
RETURNS TABLE (
    total_citations BIGINT,
    unique_documents BIGINT,
    avg_confidence FLOAT,
    source_types JSON
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) as total_citations,
        COUNT(DISTINCT document_id) as unique_documents,
        AVG(confidence_score) as avg_confidence,
        jsonb_agg(DISTINCT citation_metadata->>'source_type') as source_types
    FROM message_citations
    WHERE message_citations.message_id = p_message_id;
END;
$$ LANGUAGE plpgsql;