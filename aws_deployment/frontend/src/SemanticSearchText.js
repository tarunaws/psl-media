import React, { useState, useEffect } from 'react';
import axios from 'axios';
import styled from 'styled-components';

const PageWrapper = styled.div`
  display: flex;
  min-height: 100vh;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
`;

const Sidebar = styled.div`
  width: 280px;
  background: #f8f9fa;
  border-right: 1px solid #e0e0e0;
  padding: 20px;
  overflow-y: auto;
  max-height: 100vh;
  position: sticky;
  top: 0;
`;

const SidebarTitle = styled.h3`
  font-size: 1.2rem;
  color: #333;
  margin: 0 0 20px 0;
  display: flex;
  align-items: center;
  gap: 8px;
`;

const CatalogueItem = styled.div`
  background: white;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
  cursor: pointer;
  border: 2px solid ${props => props.isSelected ? '#667eea' : 'transparent'};
  transition: all 0.2s;
  
  &:hover {
    border-color: #667eea;
    transform: translateX(4px);
  }
`;

const CatalogueThumb = styled.div`
  width: 100%;
  height: 80px;
  background: ${props => props.src ? `url(data:image/jpeg;base64,${props.src})` : '#e0e0e0'};
  background-size: cover;
  background-position: center;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  font-size: 2rem;
  margin-bottom: 8px;
`;

const CatalogueTitle = styled.div`
  font-size: 0.9rem;
  font-weight: 600;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`;

const CatalogueMeta = styled.div`
  font-size: 0.75rem;
  color: #666;
  margin-top: 4px;
`;

const DeleteButton = styled.button`
  background: #ff4444;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 0.75rem;
  cursor: pointer;
  margin-top: 8px;
  transition: background 0.2s;
  width: 100%;
  
  &:hover {
    background: #cc0000;
  }
`;

const Container = styled.div`
  flex: 1;
  max-width: 1400px;
  margin: 0 auto;
  padding: 40px 20px;
  width: 100%;
`;

const Header = styled.div`
  text-align: center;
  margin-bottom: 50px;
`;

const Title = styled.h1`
  font-size: 2.5rem;
  color: #1a1a1a;
  margin-bottom: 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
`;

const Subtitle = styled.p`
  font-size: 1.1rem;
  color: #666;
`;

const Section = styled.div`
  background: white;
  border-radius: 12px;
  padding: 30px;
  margin-bottom: 30px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
`;

const SectionTitle = styled.h2`
  font-size: 1.5rem;
  color: #333;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
`;

const Icon = styled.span`
  font-size: 1.8rem;
`;

const Input = styled.input`
  padding: 12px 16px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 1rem;
  width: 100%;
  margin-bottom: 15px;
  
  &:focus {
    outline: none;
    border-color: #667eea;
  }
`;

const Button = styled.button`
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 12px 32px;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s;
  
  &:hover {
    transform: translateY(-2px);
  }
  
  &:disabled {
    background: #ccc;
    cursor: not-allowed;
    transform: none;
  }
`;

const SearchBox = styled.div`
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
`;

const SearchInput = styled.input`
  flex: 1;
  padding: 14px 20px;
  border: 2px solid #ddd;
  border-radius: 8px;
  font-size: 1.1rem;
  
  &:focus {
    outline: none;
    border-color: #667eea;
  }
`;

const SearchButton = styled(Button)`
  padding: 14px 40px;
`;

const ProgressBar = styled.div`
  width: 100%;
  height: 6px;
  background: #f0f0f0;
  border-radius: 3px;
  overflow: hidden;
  margin: 20px 0;
`;

const ProgressFill = styled.div`
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  width: ${props => props.percent}%;
  transition: width 0.3s;
`;

const Message = styled.div`
  padding: 12px 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  background: ${props => props.type === 'error' ? '#fee' : '#efe'};
  color: ${props => props.type === 'error' ? '#c33' : '#363'};
  border-left: 4px solid ${props => props.type === 'error' ? '#c33' : '#363'};
`;

const EmptyState = styled.div`
  text-align: center;
  padding: 60px 20px;
  color: #999;
`;

const EmptyIcon = styled.div`
  font-size: 4rem;
  margin-bottom: 20px;
`;

const BACKEND_URL = 'http://localhost:5008';

function SemanticSearchText() {
  const [message, setMessage] = useState(null);
  
  // Document state
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [documentTitle, setDocumentTitle] = useState('');
  const [uploadingDoc, setUploadingDoc] = useState(false);
  const [uploadDocProgress, setUploadDocProgress] = useState(0);
  const [allDocuments, setAllDocuments] = useState([]);
  const [textSearchQuery, setTextSearchQuery] = useState('');
  const [textSearching, setTextSearching] = useState(false);
  const [textSearchResults, setTextSearchResults] = useState([]);
  const [activeDocumentId, setActiveDocumentId] = useState(null);

  useEffect(() => {
    loadAllDocuments();
  }, []);
  
  const loadAllDocuments = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/documents`);
      setAllDocuments(response.data.documents || []);
    } catch (error) {
      console.error('Failed to load documents:', error);
    }
  };
  
  const handleDocumentSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedDocument(file);
      if (!documentTitle) {
        setDocumentTitle(file.name.replace(/\.[^/.]+$/, ''));
      }
    }
  };
  
  const handleDocumentUpload = async () => {
    if (!selectedDocument) {
      setMessage({ type: 'error', text: 'Please select a document file' });
      return;
    }

    setUploadingDoc(true);
    setUploadDocProgress(0);
    setMessage(null);

    const formData = new FormData();
    formData.append('document', selectedDocument);
    formData.append('title', documentTitle || selectedDocument.name);

    try {
      const response = await axios.post(`${BACKEND_URL}/upload-document`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadDocProgress(percentCompleted);
        }
      });

      setMessage({ 
        type: 'success', 
        text: `Document indexed successfully! ${response.data.chunks_count} chunks created.` 
      });
      
      setSelectedDocument(null);
      setDocumentTitle('');
      loadAllDocuments();
      
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.error || 'Failed to upload document' 
      });
    } finally {
      setUploadingDoc(false);
      setUploadDocProgress(0);
    }
  };
  
  const handleTextSearch = async () => {
    if (!textSearchQuery.trim()) {
      setMessage({ type: 'error', text: 'Please enter a text search query' });
      return;
    }

    setTextSearching(true);
    setMessage(null);

    try {
      const response = await axios.post(`${BACKEND_URL}/search-text`, {
        query: textSearchQuery,
        top_k: 5
      });

      setTextSearchResults(response.data.results);
      
      if (response.data.results.length === 0) {
        setMessage({ type: 'info', text: 'No matching documents found. Try a different query.' });
      }
      
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.error || 'Text search failed' 
      });
    } finally {
      setTextSearching(false);
    }
  };

  const handleDeleteDocument = async (documentId, documentTitle) => {
    if (!window.confirm(`Are you sure you want to delete "${documentTitle}"?`)) {
      return;
    }

    try {
      await axios.delete(`${BACKEND_URL}/documents/${documentId}`);
      setMessage({ 
        type: 'success', 
        text: `Document "${documentTitle}" deleted successfully.` 
      });
      
      // Clear active selection if deleted document was selected
      if (activeDocumentId === documentId) {
        setActiveDocumentId(null);
      }
      
      loadAllDocuments();
      
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.error || 'Failed to delete document' 
      });
    }
  };

  return (
    <PageWrapper>
      <Sidebar>
        <SidebarTitle>
          <span>�</span>
          Documents ({allDocuments.length})
        </SidebarTitle>
          {allDocuments.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#999', padding: '20px 0' }}>
            <div style={{ fontSize: '2rem', marginBottom: '10px' }}>�</div>
            <p style={{ fontSize: '0.85rem' }}>No documents yet</p>
          </div>
        ) : (
          allDocuments.map(doc => (
            <CatalogueItem
              key={doc.id}
              isSelected={activeDocumentId === doc.id}
            >
              <div onClick={() => setActiveDocumentId(doc.id)}>
                <CatalogueThumb src={null}>
                  📄
                </CatalogueThumb>
                <CatalogueTitle>{doc.title}</CatalogueTitle>
                <CatalogueMeta>
                  {doc.chunks_count} chunks • {new Date(doc.uploaded_at).toLocaleDateString()}
                </CatalogueMeta>
              </div>
              <DeleteButton onClick={(e) => {
                e.stopPropagation();
                handleDeleteDocument(doc.id, doc.title);
              }}>
                🗑️ Delete
              </DeleteButton>
            </CatalogueItem>
          ))
        )}
      </Sidebar>
      
      <Container>
        <Header>
          <Title>📄 Semantic Search (Text)</Title>
          <Subtitle>Upload documents and search them using natural language.</Subtitle>
        </Header>

        {message && (
          <Message type={message.type}>{message.text}</Message>
        )}      <Section>
        <SectionTitle>
          <Icon>📤</Icon>
          Upload Document
        </SectionTitle>

        <div style={{ marginBottom: '20px' }}>
          <input
            id="docInput"
            type="file"
            accept=".pdf,.txt,.doc,.docx"
            onChange={handleDocumentSelect}
            style={{ display: 'none' }}
          />
          <Button onClick={() => document.getElementById('docInput').click()}>
            Choose Document
          </Button>
          {selectedDocument && (
            <div style={{ marginTop: '10px', color: '#666' }}>
              📄 {selectedDocument.name} ({(selectedDocument.size / 1024).toFixed(2)} KB)
            </div>
          )}
        </div>

        {selectedDocument && (
          <div>
            <Input
              type="text"
              placeholder="Document Title"
              value={documentTitle}
              onChange={(e) => setDocumentTitle(e.target.value)}
            />
            <Button onClick={handleDocumentUpload} disabled={uploadingDoc}>
              {uploadingDoc ? 'Uploading...' : 'Upload & Index Document'}
            </Button>

            {uploadingDoc && (
              <ProgressBar>
                <ProgressFill percent={uploadDocProgress} />
              </ProgressBar>
            )}
          </div>
        )}
      </Section>

      <Section>
        <SectionTitle>
          <Icon>🔎</Icon>
          Search Documents (Text)
        </SectionTitle>

        <SearchBox>
          <SearchInput
            type="text"
            placeholder="Search documents by content or keywords..."
            value={textSearchQuery}
            onChange={(e) => setTextSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleTextSearch()}
          />
          <SearchButton onClick={handleTextSearch} disabled={textSearching}>
            {textSearching ? 'Searching...' : 'Search Text'}
          </SearchButton>
        </SearchBox>

        {textSearchResults.length > 0 && (
          <div style={{ marginTop: '20px', background: '#f8f9fa', padding: '20px', borderRadius: '8px' }}>
            <h3 style={{ marginTop: 0 }}>Text Search Results ({textSearchResults.filter(r => r.similarity_score >= 0.51).length})</h3>
            {textSearchResults
              .filter((result) => result.similarity_score >= 0.51)
              .map((result, idx) => (
              <div key={idx} style={{ 
                background: 'white', 
                padding: '15px', 
                marginBottom: '10px', 
                borderRadius: '8px',
                borderLeft: '4px solid #667eea'
              }}>
                <div style={{ fontWeight: 'bold', marginBottom: '8px', color: '#333' }}>
                  📄 {result.document_title}
                </div>
                <div style={{ color: '#666', lineHeight: '1.6' }}>
                  {result.text}
                </div>
                <div style={{ marginTop: '8px', fontSize: '0.85rem', color: '#999' }}>
                  Similarity: {(result.similarity_score * 100).toFixed(1)}%
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>

      {/* Q&A removed: semantic search now returns text blocks where the query appears */}

      {allDocuments.length === 0 && !uploadingDoc && (
        <EmptyState>
          <EmptyIcon>�</EmptyIcon>
          <h3>No documents indexed yet</h3>
          <p>Upload your first document to get started</p>
        </EmptyState>
      )}
      </Container>
    </PageWrapper>
  );
}

export default SemanticSearchText;
