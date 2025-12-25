# Semantic Search Text System - Architecture & Logic Guide
## Part 1: System Overview & Architecture

**Document Version:** 1.0  
**Last Updated:** October 24, 2025  
**System:** MediaGenAI - AI-Powered Semantic Search for Text Documents

---

## Table of Contents (Part 1)

1. [Executive Summary](#executive-summary)
2. [System Architecture Overview](#system-architecture-overview)
3. [Technology Stack](#technology-stack)
4. [Core Components](#core-components)
5. [Data Flow Architecture](#data-flow-architecture)
6. [AWS Services Integration](#aws-services-integration)
7. [File Storage Architecture](#file-storage-architecture)

---

## Executive Summary

### What is Semantic Search Text?

The Semantic Search Text system is an AI-powered document management and search platform that enables users to:

1. **Upload documents** in multiple formats (PDF, DOCX, TXT)
2. **Extract and chunk text** from uploaded documents
3. **Generate semantic embeddings** using AWS Bedrock Titan
4. **Search by meaning** rather than exact keywords
5. **Find relevant content** across all indexed documents
6. **Ask questions** about documents using Meta Llama AI
7. **Manage document catalog** with preview and deletion

### Key Capabilities

| Feature | Description | Technology |
|---------|-------------|------------|
| **Multi-Format Support** | PDF, DOCX, DOC, TXT files | PyPDF2, python-docx |
| **Semantic Understanding** | Meaning-based search vs keyword matching | AWS Bedrock Titan Embeddings |
| **Intelligent Chunking** | Documents split into semantic paragraphs | Python text processing |
| **AI Question Answering** | Ask natural language questions about documents | Meta Llama 3 70B via Bedrock |
| **Document Cataloging** | Organized sidebar with metadata | React + Local storage |
| **Real-time Search** | Instant semantic similarity matching | Cosine similarity algorithm |
| **Persistent Index** | Survives service restarts | JSON file storage |
| **Cross-Document Search** | Search across all uploaded documents | Multi-document embedding search |

### Key Features

- **Smart Text Extraction**: Automatically extracts text from PDF, DOCX, and TXT files
- **Paragraph-Level Chunking**: Splits documents into meaningful chunks for better search precision
- **Vector Embeddings**: Converts text to 1536-dimensional vectors for semantic understanding
- **Similarity Scoring**: Returns results ranked by relevance (0.0-1.0 scale)
- **AskMe Chatbot**: AI assistant that answers questions about MediaGenAI documentation
- **Document Management**: Upload, view, search, and delete documents
- **Sidebar Navigation**: Quick access to all indexed documents
- **Responsive UI**: Modern React interface with styled-components

---

## System Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Layer                            │
│  React SPA (SemanticSearchText.js - 737 lines)                  │
│  • Document upload UI                                            │
│  • Search interface                                              │
│  • Results display                                               │
│  • Document catalog sidebar                                      │
└────────────────┬────────────────────────────────────────────────┘
                 │ HTTP/REST API
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Application Layer                            │
│  Flask Backend (app.py - 942 lines)                             │
│  • API endpoints (9 routes)                                      │
│  • Document processing pipeline                                  │
│  • Search orchestration                                          │
│  • Q&A chatbot                                                   │
└────────────────┬────────────────────────────────────────────────┘
                 │ AWS SDK (boto3)
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AWS Services Layer                            │
│  • Bedrock Runtime (Titan Embeddings, Llama 3)                  │
│  • Amazon Comprehend (Optional: entity extraction)              │
└─────────────────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Storage Layer                                 │
│  • Local File Storage (documents/)                               │
│  • JSON Index Files (indices/)                                   │
│  • In-Memory Index (DOCUMENT_INDEX list)                        │
└─────────────────────────────────────────────────────────────────┘
```

### Architecture Layers

#### 1. Frontend Layer (React)
- **Component**: SemanticSearchText.js (737 lines)
- **Responsibilities**:
  - Document file selection and upload
  - Search query input and submission
  - Results rendering with similarity scores
  - Document catalog management
  - Delete operations
- **State Management**: React Hooks (useState, useEffect)
- **Styling**: styled-components (43+ styled elements)

#### 2. Application Layer (Flask)
- **Component**: app.py (942 lines)
- **Responsibilities**:
  - REST API endpoint handling
  - Document text extraction (PDF, DOCX, TXT)
  - Text chunking and preprocessing
  - Embedding generation coordination
  - Semantic search execution
  - Q&A chatbot logic
  - Index persistence
- **Port**: 5008
- **CORS**: Enabled for frontend communication

#### 3. AWS Services Layer
- **Bedrock Runtime**: Text embeddings and LLM inference
- **Models Used**:
  - `amazon.titan-embed-text-v1`: 1536-dimensional embeddings
  - `meta.llama3-70b-instruct-v1:0`: Question answering

#### 4. Storage Layer
- **Local Documents**: `semanticSearch/documents/`
- **Index Files**: `semanticSearch/indices/`
  - `document_index.json`: Metadata and embeddings
- **In-Memory**: Python lists for fast access

---

## Technology Stack

### Backend Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Runtime** | Python | 3.8+ | Backend application |
| **Web Framework** | Flask | 3.0+ | REST API server |
| **CORS** | flask-cors | 4.0+ | Cross-origin requests |
| **AWS SDK** | boto3 | Latest | AWS service integration |
| **PDF Processing** | PyPDF2 | Latest | PDF text extraction |
| **DOCX Processing** | python-docx | Latest | Word document parsing |
| **Environment** | python-dotenv | 1.0+ | Configuration management |

### Frontend Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Framework** | React | 18.2+ | UI framework |
| **Styling** | styled-components | 6.1+ | CSS-in-JS styling |
| **HTTP Client** | axios | 1.6+ | API communication |
| **State** | React Hooks | Built-in | State management |

### AWS Services

| Service | Purpose | Model/Feature |
|---------|---------|---------------|
| **Amazon Bedrock** | Text embeddings | Titan Embed Text v1 |
| **Amazon Bedrock** | Question answering | Meta Llama 3 70B Instruct |
| **Amazon Comprehend** | Entity extraction (optional) | Key phrase detection |

### Infrastructure

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **File Storage** | Local filesystem | Document storage |
| **Index Storage** | JSON files | Persistent metadata |
| **Memory Cache** | Python lists | Fast search access |

---

## Core Components

### 1. Flask Application (`app.py`)

**Purpose**: Core orchestration service for document indexing and search

**Key Sections**:
- Lines 1-40: Imports, AWS client initialization
- Lines 41-81: Configuration (paths, bucket, FFmpeg)
- Lines 82-130: Index management (save/load functions)
- Lines 132-139: Health check endpoint
- Lines 288-304: Embedding generation
- Lines 306-321: Similarity computation
- Lines 553-592: Text extraction from files
- Lines 594-676: Document upload and indexing
- Lines 678-708: Document listing and deletion
- Lines 710-769: Text search
- Lines 771-825: Q&A chatbot (AskMe)
- Lines 827-942: Documentation chatbot

**Configuration Variables**:

```python
# AWS Configuration
DEFAULT_AWS_REGION = "us-east-1"
bedrock_runtime = boto3.client("bedrock-runtime", region_name=DEFAULT_AWS_REGION)
comprehend = boto3.client("comprehend", region_name=DEFAULT_AWS_REGION)

# Storage Directories
STORAGE_BASE_DIR = Path(__file__).parent
DOCUMENTS_DIR = STORAGE_BASE_DIR / "documents"
INDICES_DIR = STORAGE_BASE_DIR / "indices"

# Index Files
DOCUMENT_INDEX_FILE = INDICES_DIR / "document_index.json"

# In-Memory Index
DOCUMENT_INDEX = []  # List of document dictionaries

# File Upload Limits
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB
```

### 2. Document Index Structure

Each document entry in `DOCUMENT_INDEX` contains:

```python
{
    "id": "550e8400-e29b-41d4-a716-446655440000",  # UUID
    "title": "User-provided or filename",
    "original_filename": "report.pdf",
    "stored_filename": "550e8400-e29b-41d4-a716-446655440000.pdf",
    "file_path": "/path/to/semanticSearch/documents/550e8400.pdf",
    "chunks": [
        {
            "text": "First paragraph of document...",
            "embedding": [0.123, -0.456, 0.789, ...]  # 1536 floats
        },
        {
            "text": "Second paragraph of document...",
            "embedding": [0.234, -0.567, 0.890, ...]
        }
    ],
    "chunks_count": 25,
    "full_text": "Complete document text...",
    "uploaded_at": "2025-10-24T10:30:45.123456"
}
```

### 3. Frontend Component (`SemanticSearchText.js`)

**Purpose**: Complete UI for document upload and semantic search

**Key Sections**:
- Lines 1-100: Imports, styled components (sidebar, catalog)
- Lines 100-440: Additional styled components (UI elements)
- Lines 446-736: Main component logic and JSX

**State Variables**:

```javascript
const [message, setMessage] = useState(null);              // Success/error messages
const [selectedDocument, setSelectedDocument] = useState(null);  // File object
const [documentTitle, setDocumentTitle] = useState('');    // User-provided title
const [uploadingDoc, setUploadingDoc] = useState(false);   // Upload in progress
const [uploadDocProgress, setUploadDocProgress] = useState(0);  // 0-100
const [allDocuments, setAllDocuments] = useState([]);      // Catalog list
const [textSearchQuery, setTextSearchQuery] = useState('');  // Search input
const [textSearching, setTextSearching] = useState(false);  // Search in progress
const [textSearchResults, setTextSearchResults] = useState([]);  // Results array
const [activeDocumentId, setActiveDocumentId] = useState(null);  // Selected doc
```

---

## Data Flow Architecture

### Document Upload Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ Stage 1: User Selection                                         │
│ • User selects PDF/DOCX/TXT file                                │
│ • Frontend validates file type                                  │
│ • User optionally enters title                                  │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 2: Upload                                                  │
│ • FormData created with file and title                          │
│ • POST /upload-document                                          │
│ • Progress tracking (0-100%)                                     │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 3: Text Extraction                                         │
│ • Backend detects file extension                                │
│ • PDF: PyPDF2.PdfReader extracts pages                          │
│ • DOCX: python-docx extracts paragraphs                         │
│ • TXT: Direct UTF-8 decode                                      │
│ • Result: Full text string                                      │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 4: Chunking                                                │
│ • Text split by double newlines (\n\n)                          │
│ • Empty chunks removed                                           │
│ • Fallback: First 1000 chars if no paragraphs                   │
│ • Result: List of text chunks                                   │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 5: Embedding Generation                                    │
│ • For each chunk:                                                │
│   - Call Bedrock Titan Embed Text v1                            │
│   - Input: chunk text                                            │
│   - Output: 1536-dimensional vector                              │
│ • Result: List of {text, embedding} objects                     │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 6: Indexing                                                │
│ • Create document entry with:                                    │
│   - UUID                                                         │
│   - Title, filename, file path                                  │
│   - All chunks with embeddings                                  │
│   - Full text                                                    │
│   - Timestamp                                                    │
│ • Append to DOCUMENT_INDEX                                      │
│ • Save to document_index.json                                   │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 7: Completion                                              │
│ • Return success response                                        │
│ • Frontend updates catalog                                       │
│ • Display success message                                        │
└─────────────────────────────────────────────────────────────────┘
```

### Search Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ Stage 1: Query Input                                             │
│ • User enters natural language query                             │
│ • Example: "What are the benefits of AI?"                       │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 2: Query Embedding                                         │
│ • POST /search-text with query                                   │
│ • Backend calls Bedrock Titan Embed                              │
│ • Input: query string                                            │
│ • Output: 1536-dimensional query vector                          │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 3: Similarity Computation                                  │
│ • For each document in DOCUMENT_INDEX:                           │
│   - For each chunk in document:                                  │
│     * Compute cosine similarity                                  │
│     * Formula: dot(query, chunk) / (||query|| * ||chunk||)      │
│     * Result: Score 0.0-1.0                                     │
│ • Collect all chunk results                                      │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 4: Ranking                                                 │
│ • Sort all chunks by similarity score (descending)               │
│ • Take top_k results (default: 5)                               │
│ • Build result objects with:                                     │
│   - Document title and ID                                       │
│   - Matching chunk text                                          │
│   - Similarity score                                             │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 5: Display Results                                         │
│ • Frontend filters results ≥ 0.4 similarity                     │
│ • Display each result with:                                      │
│   - Document title                                               │
│   - Matching text snippet                                        │
│   - Similarity percentage                                        │
│ • Results ranked by relevance                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## AWS Services Integration

### Amazon Bedrock - Titan Embeddings

**Model**: `amazon.titan-embed-text-v1`

**Purpose**: Convert text into semantic vector embeddings

**API Call**:

```python
response = bedrock_runtime.invoke_model(
    modelId="amazon.titan-embed-text-v1",
    contentType="application/json",
    accept="application/json",
    body=json.dumps({"inputText": text})
)

response_body = json.loads(response["body"].read())
embedding = response_body.get("embedding", [])  # 1536 floats
```

**Input**: Text string (any length)
**Output**: Array of 1536 floating-point numbers
**Use Cases**:
- Document chunk embeddings during upload
- Query embeddings during search
- Semantic similarity computation

### Amazon Bedrock - Meta Llama 3

**Model**: `meta.llama3-70b-instruct-v1:0`

**Purpose**: Answer questions about documents using context

**API Call**:

```python
response = bedrock_runtime.invoke_model(
    modelId="meta.llama3-70b-instruct-v1:0",
    contentType="application/json",
    accept="application/json",
    body=json.dumps({
        "prompt": prompt,
        "max_gen_len": 512,
        "temperature": 0.7,
        "top_p": 0.9
    })
)

response_body = json.loads(response["body"].read())
answer = response_body.get("generation", "").strip()
```

**Input**: Prompt with context and question
**Output**: Natural language answer
**Use Cases**:
- Q&A chatbot (`/ask-question`)
- AskMe documentation assistant (`/askme`)

### Amazon Comprehend (Optional)

**Purpose**: Extract entities and key phrases from documents

**Not currently used in production** but available for:
- Named entity recognition (people, places, organizations)
- Key phrase extraction
- Sentiment analysis

---

## File Storage Architecture

### Directory Structure

```
semanticSearch/
├── app.py                      # Flask backend (942 lines)
├── documents/                  # Uploaded documents
│   ├── {uuid}.pdf
│   ├── {uuid}.docx
│   └── {uuid}.txt
├── indices/                    # Persistent index files
│   ├── document_index.json    # Text document index
│   └── video_index.json       # Video index (separate feature)
└── videos/                     # Video files (separate feature)
```

### Document Storage

**Storage Path**: `semanticSearch/documents/{uuid}{extension}`

**Naming Convention**:
- UUID v4 for uniqueness
- Original file extension preserved
- Example: `550e8400-e29b-41d4-a716-446655440000.pdf`

**File Formats Supported**:
- `.pdf` - Portable Document Format
- `.docx`, `.doc` - Microsoft Word
- `.txt` - Plain text

### Index File Format

**File**: `semanticSearch/indices/document_index.json`

**Format**: JSON array of document objects

**Example**:

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "AI Research Report",
    "original_filename": "ai_report.pdf",
    "stored_filename": "550e8400-e29b-41d4-a716-446655440000.pdf",
    "file_path": "/path/to/semanticSearch/documents/550e8400.pdf",
    "chunks": [
      {
        "text": "Artificial intelligence is transforming industries...",
        "embedding": [0.123, -0.456, 0.789, ...]
      }
    ],
    "chunks_count": 15,
    "full_text": "Complete document text...",
    "uploaded_at": "2025-10-24T10:30:45.123456"
  }
]
```

### In-Memory Index

**Variable**: `DOCUMENT_INDEX` (Python list)

**Purpose**:
- Fast search operations (no disk I/O)
- Loaded on service startup
- Synchronized with JSON file on changes

**Operations**:
- **Load**: `_load_document_index()` on startup
- **Save**: `_save_document_index()` after upload/delete
- **Search**: Direct iteration over list

---

## Next Document

➡️ **Part 2: API Endpoints & Processing Logic**  
Covers all REST endpoints, request/response formats, and core algorithms.

---

*End of Part 1*
# Semantic Search Text System - Architecture & Logic Guide
## Part 2: API Endpoints & Processing Logic

**Document Version:** 1.0  
**Last Updated:** October 24, 2025  
**System:** MediaGenAI - AI-Powered Semantic Search for Text Documents

---

## Table of Contents (Part 2)

1. [API Endpoints Overview](#api-endpoints-overview)
2. [Document Upload Endpoint](#document-upload-endpoint)
3. [Text Search Endpoint](#text-search-endpoint)
4. [Document Management Endpoints](#document-management-endpoints)
5. [Q&A Chatbot Endpoint](#qa-chatbot-endpoint)
6. [AskMe Documentation Chatbot](#askme-documentation-chatbot)
7. [Core Processing Algorithms](#core-processing-algorithms)

---

## API Endpoints Overview

### Endpoint Summary

| Endpoint | Method | Purpose | Request Size |
|----------|--------|---------|--------------|
| `/health` | GET | Service health check | - |
| `/upload-document` | POST | Upload and index document | Up to 500MB |
| `/documents` | GET | List all indexed documents | - |
| `/documents/<id>` | DELETE | Delete specific document | - |
| `/search-text` | POST | Semantic search across documents | Small JSON |
| `/ask-question` | POST | Q&A about specific document | Small JSON |
| `/askme` | POST | Chat about MediaGenAI docs | Small JSON |

**Base URL**: `http://localhost:5008`

---

## Document Upload Endpoint

### POST /upload-document

**Purpose**: Upload a document (PDF/DOCX/TXT) and create searchable index

**Request Format**:

```http
POST /upload-document HTTP/1.1
Content-Type: multipart/form-data
```

**Form Data**:

```javascript
const formData = new FormData();
formData.append('document', fileObject);  // Required: File object
formData.append('title', 'My Document'); // Optional: Display title
```

**Supported File Types**:
- `.pdf` - PDF documents (via PyPDF2)
- `.docx`, `.doc` - Microsoft Word (via python-docx)
- `.txt` - Plain text files (UTF-8)

**Processing Pipeline**:

```python
def upload_document():
    # 1. Validate Request
    if "document" not in request.files:
        return jsonify({"error": "No document file provided"}), 400
    
    doc_file = request.files["document"]
    if not doc_file.filename:
        return jsonify({"error": "Empty filename"}), 400
    
    doc_title = request.form.get("title", doc_file.filename)
    doc_id = str(uuid.uuid4())
    
    # 2. Extract Text
    file_content = doc_file.read()
    original_filename = doc_file.filename
    content = _extract_text_from_file(file_content, original_filename)
    
    if not content or len(content.strip()) < 10:
        return jsonify({"error": "Could not extract text"}), 400
    
    # 3. Save to Local Storage
    file_extension = Path(original_filename).suffix or '.txt'
    stored_filename = f"{doc_id}{file_extension}"
    doc_file_path = DOCUMENTS_DIR / stored_filename
    
    with open(doc_file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 4. Chunk Text
    chunks = [chunk.strip() for chunk in content.split('\n\n') if chunk.strip()]
    if not chunks:
        chunks = [content[:1000]]  # Fallback
    
    # 5. Generate Embeddings
    chunk_embeddings = []
    for chunk in chunks:
        embedding = _generate_embedding(chunk)
        if embedding:
            chunk_embeddings.append({
                "text": chunk,
                "embedding": embedding
            })
    
    # 6. Create Index Entry
    doc_entry = {
        "id": doc_id,
        "title": doc_title,
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        "file_path": str(doc_file_path),
        "chunks": chunk_embeddings,
        "chunks_count": len(chunk_embeddings),
        "full_text": content,
        "uploaded_at": datetime.utcnow().isoformat()
    }
    
    # 7. Update Index
    DOCUMENT_INDEX.append(doc_entry)
    _save_document_index()
    
    return jsonify({
        "id": doc_id,
        "title": doc_title,
        "message": "Document uploaded and indexed successfully",
        "chunks_count": len(chunk_embeddings)
    }), 200
```

**Response Format**:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "AI Research Report",
  "message": "Document uploaded and indexed successfully",
  "chunks_count": 15
}
```

**Error Responses**:

```json
// Missing file
{
  "error": "No document file provided"
}

// Text extraction failed
{
  "error": "Could not extract text from document or document is too short"
}

// Processing error
{
  "error": "Failed to process document: {error_details}"
}
```

---

## Text Search Endpoint

### POST /search-text

**Purpose**: Search all indexed documents using semantic similarity

**Request Format**:

```http
POST /search-text HTTP/1.1
Content-Type: application/json
```

**Request Body**:

```json
{
  "query": "What are the benefits of artificial intelligence?",
  "top_k": 5
}
```

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Natural language search query |
| `top_k` | integer | No | 5 | Number of results to return |

**Processing Logic**:

```python
def search_text():
    payload = request.get_json(silent=True) or {}
    query = payload.get("query", "").strip()
    top_k = int(payload.get("top_k", 5))
    
    if not query:
        return jsonify({"error": "Query is required"}), 400
    
    if not DOCUMENT_INDEX:
        return jsonify({"error": "No documents indexed yet"}), 400
    
    # 1. Generate Query Embedding
    query_embedding = _generate_embedding(query)
    
    if not query_embedding:
        return jsonify({"error": "Failed to generate query embedding"}), 500
    
    # 2. Search All Chunks
    results = []
    for doc in DOCUMENT_INDEX:
        for chunk in doc["chunks"]:
            # Compute cosine similarity
            similarity = _compute_similarity(query_embedding, chunk["embedding"])
            results.append({
                "document_id": doc["id"],
                "document_title": doc["title"],
                "text": chunk["text"],
                "similarity_score": round(similarity, 4)
            })
    
    # 3. Sort by Similarity
    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    
    # 4. Return Top K
    return jsonify({
        "query": query,
        "results": results[:top_k]
    }), 200
```

**Response Format**:

```json
{
  "query": "What are the benefits of artificial intelligence?",
  "results": [
    {
      "document_id": "550e8400-e29b-41d4-a716-446655440000",
      "document_title": "AI Research Report",
      "text": "Artificial intelligence offers numerous benefits including automation of repetitive tasks, enhanced decision-making through data analysis, and improved efficiency across industries.",
      "similarity_score": 0.8756
    },
    {
      "document_id": "660f9511-f3ac-52e5-b827-557766551111",
      "document_title": "Machine Learning Guide",
      "text": "The advantages of AI systems include scalability, consistency in execution, and the ability to process vast amounts of information quickly.",
      "similarity_score": 0.7234
    }
  ]
}
```

**Frontend Filtering**:

The frontend filters results with similarity ≥ 0.4 (40%):

```javascript
textSearchResults
  .filter((result) => result.similarity_score >= 0.4)
  .map((result, idx) => (
    // Display result
  ))
```

**Error Responses**:

```json
// No query provided
{
  "error": "Query is required"
}

// No documents indexed
{
  "error": "No documents indexed yet"
}

// Embedding generation failed
{
  "error": "Failed to generate query embedding"
}
```

---

## Document Management Endpoints

### GET /documents

**Purpose**: List all indexed documents with metadata

**Request Format**:

```http
GET /documents HTTP/1.1
```

**No Parameters Required**

**Processing Logic**:

```python
def list_documents():
    documents = [
        {
            "id": d["id"],
            "title": d["title"],
            "chunks_count": d["chunks_count"],
            "uploaded_at": d["uploaded_at"]
        }
        for d in DOCUMENT_INDEX
    ]
    
    return jsonify({
        "documents": documents,
        "total": len(documents)
    }), 200
```

**Response Format**:

```json
{
  "documents": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "AI Research Report",
      "chunks_count": 15,
      "uploaded_at": "2025-10-24T10:30:45.123456"
    },
    {
      "id": "660f9511-f3ac-52e5-b827-557766551111",
      "title": "Machine Learning Guide",
      "chunks_count": 23,
      "uploaded_at": "2025-10-24T11:15:20.654321"
    }
  ],
  "total": 2
}
```

### DELETE /documents/<document_id>

**Purpose**: Delete a document from the index

**Request Format**:

```http
DELETE /documents/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
```

**Processing Logic**:

```python
def delete_document(document_id: str):
    global DOCUMENT_INDEX
    
    # Find document index
    doc_idx = None
    for idx, doc in enumerate(DOCUMENT_INDEX):
        if doc["id"] == document_id:
            doc_idx = idx
            break
    
    if doc_idx is None:
        return jsonify({"error": "Document not found"}), 404
    
    # Remove from index
    deleted_doc = DOCUMENT_INDEX.pop(doc_idx)
    
    # Save updated index
    _save_document_index()
    
    app.logger.info(f"Deleted document: {deleted_doc['title']} (ID: {document_id})")
    
    return jsonify({
        "message": "Document deleted successfully",
        "deleted_document": {
            "id": deleted_doc["id"],
            "title": deleted_doc["title"]
        }
    }), 200
```

**Response Format**:

```json
{
  "message": "Document deleted successfully",
  "deleted_document": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "AI Research Report"
  }
}
```

**Error Response**:

```json
{
  "error": "Document not found"
}
```

**Note**: This endpoint only removes the document from the index. The physical file remains in `documents/` directory. To also delete the file, modify the code:

```python
# Add after removing from index:
import os
if os.path.exists(deleted_doc["file_path"]):
    os.remove(deleted_doc["file_path"])
```

---

## Q&A Chatbot Endpoint

### POST /ask-question

**Purpose**: Ask natural language questions about a specific document

**Request Format**:

```http
POST /ask-question HTTP/1.1
Content-Type: application/json
```

**Request Body**:

```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "question": "What are the main conclusions of this report?"
}
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | string | Yes | UUID of the document |
| `question` | string | Yes | Natural language question |

**Processing Logic**:

```python
def ask_question():
    payload = request.get_json(silent=True) or {}
    document_id = payload.get("document_id", "").strip()
    question = payload.get("question", "").strip()
    
    if not document_id or not question:
        return jsonify({"error": "Both document_id and question are required"}), 400
    
    # 1. Find Document
    doc = next((d for d in DOCUMENT_INDEX if d["id"] == document_id), None)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    
    # 2. Generate Query Embedding
    query_embedding = _generate_embedding(question)
    
    # 3. Find Most Relevant Chunks
    chunk_scores = []
    for chunk in doc["chunks"]:
        similarity = _compute_similarity(query_embedding, chunk["embedding"])
        chunk_scores.append((chunk["text"], similarity))
    
    # Sort and get top 3 chunks
    chunk_scores.sort(key=lambda x: x[1], reverse=True)
    relevant_chunks = [chunk[0] for chunk in chunk_scores[:3]]
    
    # 4. Build Prompt for Llama
    context = "\n\n".join(relevant_chunks)
    prompt = f"""Based on the following context from the document, please answer the question.

Context:
{context}

Question: {question}

Answer:"""
    
    # 5. Call Bedrock with Meta Llama
    response = bedrock_runtime.invoke_model(
        modelId="meta.llama3-70b-instruct-v1:0",
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "prompt": prompt,
            "max_gen_len": 512,
            "temperature": 0.7,
            "top_p": 0.9
        })
    )
    
    response_body = json.loads(response["body"].read())
    answer = response_body.get("generation", "").strip()
    
    # 6. Return Answer with Context
    return jsonify({
        "question": question,
        "answer": answer,
        "context": relevant_chunks,
        "document_title": doc["title"]
    }), 200
```

**Response Format**:

```json
{
  "question": "What are the main conclusions of this report?",
  "answer": "The report concludes that AI technology is rapidly advancing and transforming multiple industries. The main findings indicate significant improvements in efficiency, accuracy, and scalability across various applications. However, challenges remain in areas of ethics, data privacy, and algorithmic bias.",
  "context": [
    "In conclusion, our research demonstrates that artificial intelligence...",
    "The study reveals three key findings: first, AI systems show remarkable...",
    "Future research should focus on addressing ethical concerns..."
  ],
  "document_title": "AI Research Report"
}
```

**RAG (Retrieval-Augmented Generation) Workflow**:

1. **Retrieval**: Find top 3 most relevant chunks using semantic similarity
2. **Augmentation**: Combine chunks into context for LLM
3. **Generation**: Meta Llama generates answer based on context
4. **Grounding**: Answer is grounded in actual document content

**Error Responses**:

```json
// Missing parameters
{
  "error": "Both document_id and question are required"
}

// Document not found
{
  "error": "Document not found"
}

// Processing error
{
  "error": "Question answering failed: {error_details}"
}
```

---

## AskMe Documentation Chatbot

### POST /askme

**Purpose**: Answer questions about MediaGenAI platform and documentation

**Request Format**:

```http
POST /askme HTTP/1.1
Content-Type: application/json
```

**Request Body**:

```json
{
  "question": "How does the semantic search feature work?"
}
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `question` | string | Yes | Question about MediaGenAI |

**Processing Logic**:

```python
def askme_chatbot():
    data = request.get_json()
    question = data.get("question", "").strip()
    
    if not question:
        return jsonify({"error": "Question is required"}), 400
    
    # 1. Load Documentation Files
    docs_dir = Path(__file__).parent.parent / "Documentation"
    readme_file = Path(__file__).parent.parent / "SERVICES_README.md"
    
    context_docs = []
    
    # Read SERVICES_README.md
    if readme_file.exists():
        with open(readme_file, 'r', encoding='utf-8') as f:
            context_docs.append({
                "filename": "SERVICES_README.md",
                "content": f.read()
            })
    
    # Read markdown documentation files
    if docs_dir.exists():
        for doc_file in docs_dir.glob("*.md"):
            with open(doc_file, 'r', encoding='utf-8') as f:
                context_docs.append({
                    "filename": doc_file.name,
                    "content": f.read()
                })
    
    # 2. Build Context (limit to prevent token overflow)
    context_text = "\n\n---\n\n".join([
        f"Document: {doc['filename']}\n\n{doc['content'][:3000]}"
        for doc in context_docs[:5]  # Top 5 documents
    ])
    
    # 3. Create Prompt
    prompt = f"""You are AskMe, a helpful chatbot assistant for MediaGenAI platform. You help users understand the various AI-powered media generation use cases available in the platform.

Documentation Context:
{context_text}

User Question: {question}

Provide a helpful, accurate, and concise answer based on the documentation above. If the question is about a specific use case or feature, explain what it does and how it works. If you're not sure about something, say so.

Answer:"""
    
    # 4. Call Bedrock Llama
    response = bedrock_runtime.invoke_model(
        modelId="meta.llama3-70b-instruct-v1:0",
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "prompt": prompt,
            "max_gen_len": 512,
            "temperature": 0.7,
            "top_p": 0.9
        })
    )
    
    response_body = json.loads(response["body"].read())
    answer = response_body.get("generation", "").strip()
    
    # 5. Return Answer with Sources
    return jsonify({
        "question": question,
        "answer": answer,
        "sources": [doc["filename"] for doc in context_docs[:5]]
    }), 200
```

**Response Format**:

```json
{
  "question": "How does the semantic search feature work?",
  "answer": "The semantic search feature in MediaGenAI uses AI embeddings to understand the meaning of your queries rather than just matching keywords. When you upload a document, it's automatically split into chunks and converted into vector embeddings using Amazon Bedrock Titan. When you search, your query is also converted to an embedding, and the system finds the most semantically similar content using cosine similarity. This allows you to find relevant information even if the exact words don't match.",
  "sources": [
    "SERVICES_README.md",
    "semantic_search_guide.md",
    "aws_integration.md"
  ]
}
```

**Key Differences from `/ask-question`**:

| Feature | `/ask-question` | `/askme` |
|---------|----------------|----------|
| **Scope** | Single uploaded document | MediaGenAI documentation |
| **Context Source** | User-uploaded file | System documentation files |
| **Use Case** | Document-specific Q&A | Platform help & guidance |
| **Requires document_id** | Yes | No |

---

## Core Processing Algorithms

### 1. Text Extraction (`_extract_text_from_file`)

**Purpose**: Extract plain text from different file formats

**Supported Formats**:

```python
def _extract_text_from_file(file_content: bytes, filename: str) -> str:
    file_extension = Path(filename).suffix.lower()
    
    try:
        if file_extension == '.pdf':
            # PDF Extraction
            pdf_reader = PdfReader(io.BytesIO(file_content))
            text_parts = []
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            return '\n\n'.join(text_parts)
        
        elif file_extension in ['.docx', '.doc']:
            # DOCX Extraction
            doc = DocxDocument(io.BytesIO(file_content))
            text_parts = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)
            return '\n\n'.join(text_parts)
        
        elif file_extension == '.txt':
            # Plain Text
            return file_content.decode('utf-8', errors='ignore')
        
        else:
            # Fallback: Try UTF-8 decode
            return file_content.decode('utf-8', errors='ignore')
    
    except Exception as e:
        app.logger.error(f"Error extracting text from {filename}: {str(e)}")
        # Final fallback
        try:
            return file_content.decode('utf-8', errors='ignore')
        except:
            return ""
```

**Error Handling**:
- Graceful degradation with fallbacks
- Invalid characters ignored with `errors='ignore'`
- Returns empty string if all methods fail

### 2. Embedding Generation (`_generate_embedding`)

**Purpose**: Convert text to 1536-dimensional vector using Bedrock Titan

**Implementation**:

```python
def _generate_embedding(text: str) -> List[float]:
    try:
        response = bedrock_runtime.invoke_model(
            modelId="amazon.titan-embed-text-v1",
            contentType="application/json",
            accept="application/json",
            body=json.dumps({"inputText": text})
        )
        
        response_body = json.loads(response["body"].read())
        embedding = response_body.get("embedding", [])
        return embedding
    except Exception as e:
        app.logger.error(f"Embedding generation failed: {e}")
        return []
```

**Characteristics**:
- **Input**: Any text string
- **Output**: Array of 1536 floats
- **Model**: Amazon Titan Embed Text v1
- **Normalization**: Pre-normalized by model
- **Performance**: ~50ms per request

### 3. Cosine Similarity (`_compute_similarity`)

**Purpose**: Measure semantic similarity between two embeddings

**Algorithm**:

```python
def _compute_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    if not embedding1 or not embedding2:
        return 0.0
    
    import math
    
    # Dot product
    dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
    
    # Magnitudes
    magnitude1 = math.sqrt(sum(a * a for a in embedding1))
    magnitude2 = math.sqrt(sum(b * b for b in embedding2))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    # Cosine similarity
    return dot_product / (magnitude1 * magnitude2)
```

**Mathematical Formula**:

$$
\text{similarity}(\vec{a}, \vec{b}) = \frac{\vec{a} \cdot \vec{b}}{||\vec{a}|| \times ||\vec{b}||} = \frac{\sum_{i=1}^{n} a_i b_i}{\sqrt{\sum_{i=1}^{n} a_i^2} \times \sqrt{\sum_{i=1}^{n} b_i^2}}
$$

**Score Interpretation**:

| Score Range | Interpretation |
|-------------|----------------|
| 0.9 - 1.0 | Highly similar (near duplicate) |
| 0.7 - 0.9 | Very relevant |
| 0.5 - 0.7 | Moderately relevant |
| 0.4 - 0.5 | Somewhat relevant |
| 0.0 - 0.4 | Not relevant |

**Frontend Threshold**: Results with similarity < 0.4 are filtered out

### 4. Text Chunking

**Purpose**: Split documents into meaningful segments

**Strategy**: Paragraph-based chunking

```python
# Split by double newlines (paragraph breaks)
chunks = [chunk.strip() for chunk in content.split('\n\n') if chunk.strip()]

# Fallback for documents without clear paragraphs
if not chunks:
    chunks = [content[:1000]]  # First 1000 characters
```

**Chunking Parameters**:

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Delimiter** | `\n\n` | Natural paragraph breaks |
| **Min chunk size** | No minimum | Preserves all content |
| **Max chunk size** | No maximum | Titan handles long text |
| **Overlap** | None | Reduces redundancy |
| **Fallback** | 1000 chars | Ensures at least one chunk |

**Alternative Strategies** (not currently implemented):

1. **Fixed-size chunking**: Split every N characters
2. **Sentence-based**: Split on periods with NLP
3. **Sliding window**: Overlapping chunks for context
4. **Semantic chunking**: Use embeddings to find natural breaks

---

## Next Document

➡️ **Part 3: Frontend Architecture & Components**  
Covers React component structure, state management, and UI implementation.

---

*End of Part 2*
# Semantic Search Text System - Architecture & Logic Guide
## Part 3: Frontend Architecture & Components

**Document Version:** 1.0  
**Last Updated:** October 24, 2025  
**System:** MediaGenAI - AI-Powered Semantic Search for Text Documents

---

## Table of Contents (Part 3)

1. [Frontend Architecture Overview](#frontend-architecture-overview)
2. [Component Structure](#component-structure)
3. [State Management](#state-management)
4. [User Interaction Flows](#user-interaction-flows)
5. [API Integration](#api-integration)
6. [UI Components](#ui-components)
7. [Styling Architecture](#styling-architecture)

---

## Frontend Architecture Overview

### Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Framework** | React | 18.2+ | Component-based UI |
| **Styling** | styled-components | 6.1+ | CSS-in-JS |
| **HTTP Client** | axios | 1.6+ | API communication |
| **State** | React Hooks | Built-in | State management |

### Component Architecture

```
SemanticSearchText (Main Component - 737 lines)
│
├── PageWrapper (Layout Container)
│   │
│   ├── Sidebar (Left Panel)
│   │   ├── SidebarTitle (Header with count)
│   │   └── Document Catalogue
│   │       ├── CatalogueItem (per document)
│   │       │   ├── CatalogueThumb (icon)
│   │       │   ├── CatalogueTitle (name)
│   │       │   ├── CatalogueMeta (chunks, date)
│   │       │   └── DeleteButton (remove)
│   │       └── EmptyState (when no docs)
│   │
│   └── Container (Main Content Area)
│       ├── Header
│       │   ├── Title
│       │   └── Subtitle
│       │
│       ├── Message (Success/Error Banner)
│       │
│       ├── Upload Section
│       │   ├── SectionTitle
│       │   ├── File Input (hidden)
│       │   ├── Choose Button
│       │   ├── File Info Display
│       │   ├── Title Input
│       │   ├── Upload Button
│       │   └── ProgressBar
│       │
│       ├── Search Section
│       │   ├── SectionTitle
│       │   ├── SearchBox
│       │   │   ├── SearchInput
│       │   │   └── SearchButton
│       │   └── Results Display
│       │       └── Result Cards (per match)
│       │
│       └── EmptyState (when no documents)
│
└── Styled Components (43 elements)
    ├── Layout (PageWrapper, Sidebar, Container)
    ├── Typography (Title, Subtitle, Labels)
    ├── Form Elements (Input, Button, etc.)
    └── Display (Cards, Messages, etc.)
```

---

## Component Structure

### Main Component: SemanticSearchText

**File**: `frontend/src/SemanticSearchText.js` (737 lines)

**Purpose**: Complete UI for document upload and semantic search

**Key Sections**:

```javascript
// Lines 1-65: Imports and styled components (sidebar)
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import styled from 'styled-components';

// Lines 67-440: Styled components (UI elements)
const PageWrapper = styled.div`...`;
const Sidebar = styled.div`...`;
// ... 40+ more styled components

// Lines 446-736: Main component logic
function SemanticSearchText() {
  // State declarations
  // Effect hooks
  // Event handlers
  // JSX rendering
}

export default SemanticSearchText;
```

### Component Breakdown

#### 1. PageWrapper (Layout)

```javascript
const PageWrapper = styled.div`
  display: flex;
  min-height: 100vh;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
`;
```

**Purpose**: Top-level container with flexbox layout
**Layout**: Horizontal split (sidebar + main content)

#### 2. Sidebar (Document Catalogue)

```javascript
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
```

**Features**:
- Fixed 280px width
- Sticky positioning (stays visible when scrolling)
- Independent scrolling for long document lists
- Light gray background (#f8f9fa)

#### 3. Container (Main Content)

```javascript
const Container = styled.div`
  flex: 1;
  max-width: 1400px;
  margin: 0 auto;
  padding: 40px 20px;
  width: 100%;
`;
```

**Features**:
- Flexible width (grows to fill space)
- Maximum width of 1400px for readability
- Centered with auto margins
- 40px top/bottom padding

---

## State Management

### State Variables

```javascript
function SemanticSearchText() {
  // UI State
  const [message, setMessage] = useState(null);
  
  // Document Upload State
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [documentTitle, setDocumentTitle] = useState('');
  const [uploadingDoc, setUploadingDoc] = useState(false);
  const [uploadDocProgress, setUploadDocProgress] = useState(0);
  
  // Document Catalogue State
  const [allDocuments, setAllDocuments] = useState([]);
  const [activeDocumentId, setActiveDocumentId] = useState(null);
  
  // Search State
  const [textSearchQuery, setTextSearchQuery] = useState('');
  const [textSearching, setTextSearching] = useState(false);
  const [textSearchResults, setTextSearchResults] = useState([]);
}
```

### State Details

| State Variable | Type | Purpose | Initial Value |
|----------------|------|---------|---------------|
| `message` | object\|null | Success/error messages | null |
| `selectedDocument` | File\|null | File to upload | null |
| `documentTitle` | string | User-provided title | "" |
| `uploadingDoc` | boolean | Upload in progress | false |
| `uploadDocProgress` | number | Upload progress (0-100) | 0 |
| `allDocuments` | array | List of indexed documents | [] |
| `activeDocumentId` | string\|null | Selected document in sidebar | null |
| `textSearchQuery` | string | Search input value | "" |
| `textSearching` | boolean | Search in progress | false |
| `textSearchResults` | array | Search results | [] |

### Message Object Structure

```javascript
setMessage({
  type: 'success' | 'error' | 'info',
  text: 'Message content here'
});
```

### Document Object Structure

```javascript
{
  id: "550e8400-e29b-41d4-a716-446655440000",
  title: "AI Research Report",
  chunks_count: 15,
  uploaded_at: "2025-10-24T10:30:45.123456"
}
```

### Search Result Object Structure

```javascript
{
  document_id: "550e8400-e29b-41d4-a716-446655440000",
  document_title: "AI Research Report",
  text: "Relevant chunk text...",
  similarity_score: 0.8756
}
```

---

## User Interaction Flows

### 1. Initial Load

```javascript
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
```

**Flow**:
1. Component mounts
2. `useEffect` triggers once (empty dependency array)
3. API call to `/documents`
4. Update `allDocuments` state
5. Sidebar renders document catalogue

### 2. Document Upload Flow

```javascript
// Step 1: File Selection
const handleDocumentSelect = (e) => {
  const file = e.target.files[0];
  if (file) {
    setSelectedDocument(file);
    // Auto-populate title from filename (without extension)
    if (!documentTitle) {
      setDocumentTitle(file.name.replace(/\.[^/.]+$/, ''));
    }
  }
};

// Step 2: Upload Execution
const handleDocumentUpload = async () => {
  // Validation
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
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        );
        setUploadDocProgress(percentCompleted);
      }
    });

    // Success
    setMessage({ 
      type: 'success', 
      text: `Document indexed successfully! ${response.data.chunks_count} chunks created.` 
    });
    
    // Reset form
    setSelectedDocument(null);
    setDocumentTitle('');
    
    // Refresh catalogue
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
```

**UI States**:

1. **Idle**: "Choose Document" button visible
2. **File Selected**: File info displayed, title input enabled
3. **Uploading**: Progress bar visible, button disabled
4. **Success**: Green message, catalogue refreshed
5. **Error**: Red error message displayed

### 3. Search Flow

```javascript
const handleTextSearch = async () => {
  // Validation
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
    
    // No results message
    if (response.data.results.length === 0) {
      setMessage({ 
        type: 'info', 
        text: 'No matching documents found. Try a different query.' 
      });
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
```

**Trigger Methods**:
1. Click "Search Text" button
2. Press Enter key in search input

```javascript
<SearchInput
  onKeyPress={(e) => e.key === 'Enter' && handleTextSearch()}
/>
```

### 4. Document Deletion Flow

```javascript
const handleDeleteDocument = async (documentId, documentTitle) => {
  // Confirmation dialog
  if (!window.confirm(`Are you sure you want to delete "${documentTitle}"?`)) {
    return;
  }

  try {
    await axios.delete(`${BACKEND_URL}/documents/${documentId}`);
    
    setMessage({ 
      type: 'success', 
      text: `Document "${documentTitle}" deleted successfully.` 
    });
    
    // Clear selection if deleted document was active
    if (activeDocumentId === documentId) {
      setActiveDocumentId(null);
    }
    
    // Refresh catalogue
    loadAllDocuments();
    
  } catch (error) {
    setMessage({ 
      type: 'error', 
      text: error.response?.data?.error || 'Failed to delete document' 
    });
  }
};
```

**Safety Features**:
- Browser confirmation dialog
- Active selection cleared if deleted
- Immediate catalogue refresh
- Error handling with user feedback

---

## API Integration

### API Base URL

```javascript
const BACKEND_URL = 'http://localhost:5008';
```

**Environment Configuration** (recommended enhancement):

```javascript
const BACKEND_URL = process.env.REACT_APP_SEMANTIC_SEARCH_API 
  || 'http://localhost:5008';
```

### Axios Configurations

#### 1. Document Upload

```javascript
axios.post(`${BACKEND_URL}/upload-document`, formData, {
  headers: { 
    'Content-Type': 'multipart/form-data' 
  },
  onUploadProgress: (progressEvent) => {
    const percentCompleted = Math.round(
      (progressEvent.loaded * 100) / progressEvent.total
    );
    setUploadDocProgress(percentCompleted);
  }
})
```

**Features**:
- Multipart form data for file upload
- Progress tracking callback
- Percentage calculation

#### 2. Text Search

```javascript
axios.post(`${BACKEND_URL}/search-text`, {
  query: textSearchQuery,
  top_k: 5
})
```

**Features**:
- JSON payload
- Simple request/response
- Default top_k of 5 results

#### 3. Document List

```javascript
axios.get(`${BACKEND_URL}/documents`)
```

**Features**:
- Simple GET request
- No parameters needed

#### 4. Document Delete

```javascript
axios.delete(`${BACKEND_URL}/documents/${documentId}`)
```

**Features**:
- RESTful URL parameter
- No request body needed

### Error Handling Pattern

```javascript
try {
  const response = await axios.post(url, data);
  // Success handling
} catch (error) {
  setMessage({ 
    type: 'error', 
    text: error.response?.data?.error || 'Generic error message' 
  });
}
```

**Error Priority**:
1. `error.response?.data?.error` - Backend error message
2. Fallback generic message

---

## UI Components

### 1. Document Catalogue Sidebar

```jsx
<Sidebar>
  <SidebarTitle>
    <span>📚</span>
    Documents ({allDocuments.length})
  </SidebarTitle>
  
  {allDocuments.length === 0 ? (
    <div style={{ textAlign: 'center', color: '#999', padding: '20px 0' }}>
      <div style={{ fontSize: '2rem', marginBottom: '10px' }}>📭</div>
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
```

**Features**:
- Document count in header
- Empty state with emoji
- Clickable document cards
- Highlight selected document
- Delete button with event propagation stop
- Date formatting with `toLocaleDateString()`

### 2. Upload Section

```jsx
<Section>
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
```

**Features**:
- Hidden file input (triggered by button)
- File type restrictions (`.pdf,.txt,.doc,.docx`)
- File size display in KB
- Conditional rendering based on state
- Progress bar during upload
- Button text changes during upload

### 3. Search Section

```jsx
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
      <h3 style={{ marginTop: 0 }}>
        Text Search Results ({textSearchResults.filter(r => r.similarity_score >= 0.4).length})
      </h3>
      {textSearchResults
        .filter((result) => result.similarity_score >= 0.4)
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
```

**Features**:
- Enter key triggers search
- Button disabled during search
- Results filtered by 0.4 threshold
- Similarity percentage display
- Visual hierarchy with colors
- Document title with emoji
- Left border accent (#667eea brand color)

### 4. Message Banner

```jsx
{message && (
  <Message type={message.type}>{message.text}</Message>
)}
```

```javascript
const Message = styled.div`
  padding: 12px 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  background: ${props => props.type === 'error' ? '#fee' : '#efe'};
  color: ${props => props.type === 'error' ? '#c33' : '#363'};
  border-left: 4px solid ${props => props.type === 'error' ? '#c33' : '#363'};
`;
```

**Types**:
- **success**: Green background (#efe), green text (#363)
- **error**: Red background (#fee), red text (#c33)
- **info**: (uses success styling)

---

## Styling Architecture

### Styled Components Pattern

**Advantages**:
- Component-scoped CSS (no global conflicts)
- Dynamic styling with props
- Type-safe with TypeScript
- Co-location of styles and components

### Color Palette

| Color | Hex Code | Usage |
|-------|----------|-------|
| **Primary Purple** | #667eea | Brand color, buttons, accents |
| **Secondary Purple** | #764ba2 | Gradients |
| **Dark Gray** | #1a1a1a | Primary text |
| **Medium Gray** | #666 | Secondary text |
| **Light Gray** | #f8f9fa | Backgrounds |
| **Border Gray** | #e0e0e0 | Dividers |
| **Success Green** | #363 | Success messages |
| **Error Red** | #c33 | Error messages |

### Typography

```javascript
const Title = styled.h1`
  font-size: 2.5rem;
  color: #1a1a1a;
  margin-bottom: 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
`;
```

**Gradient Text Effect**:
- Linear gradient background
- Background clipping to text
- Transparent fill color
- Creates colorful text effect

### Button Styles

```javascript
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
```

**Features**:
- Gradient background (brand colors)
- Hover effect (lift up 2px)
- Disabled state (gray, no hover)
- Smooth transition

### Responsive Design

```javascript
const Container = styled.div`
  flex: 1;
  max-width: 1400px;
  margin: 0 auto;
  padding: 40px 20px;
  width: 100%;
`;
```

**Breakpoint Strategy** (not currently implemented):

```javascript
const Container = styled.div`
  flex: 1;
  max-width: 1400px;
  margin: 0 auto;
  padding: 40px 20px;
  width: 100%;
  
  @media (max-width: 768px) {
    padding: 20px 10px;
  }
`;

const Sidebar = styled.div`
  width: 280px;
  
  @media (max-width: 1024px) {
    width: 200px;
  }
  
  @media (max-width: 768px) {
    display: none; // Or convert to drawer
  }
`;
```

---

## Key Frontend Features

### 1. Progressive Disclosure

- Upload section only shows title input after file selection
- Progress bar only visible during upload
- Results section only shown when there are results

### 2. Real-Time Feedback

- Upload progress tracking (0-100%)
- Button text changes ("Uploading...", "Searching...")
- Immediate error/success messages
- Disabled buttons during operations

### 3. User Experience Enhancements

- Auto-populate document title from filename
- Enter key triggers search
- Confirmation dialog before deletion
- File size display in human-readable format
- Date formatting with locale-aware function
- Emoji icons for visual appeal

### 4. Performance Optimizations

- Conditional rendering (avoid unnecessary DOM)
- Event propagation stop on nested clicks
- Single API call on mount for document list
- Filtered results client-side (≥0.4 threshold)

### 5. Accessibility Considerations

- Semantic HTML (sections, buttons, inputs)
- Clear labels and placeholders
- Visual feedback for all actions
- Keyboard navigation support (Enter key)

---

## Next Document

➡️ **Part 4: Deployment & Operations**  
Covers environment setup, service management, and troubleshooting.

---

*End of Part 3*
# Semantic Search Text System - Architecture & Logic Guide
## Part 4: Deployment & Operations

**Document Version:** 1.0  
**Last Updated:** October 24, 2025  
**System:** MediaGenAI - AI-Powered Semantic Search for Text Documents

---

## Table of Contents (Part 4)

1. [Environment Setup](#environment-setup)
2. [Service Configuration](#service-configuration)
3. [Deployment Procedures](#deployment-procedures)
4. [Monitoring & Logging](#monitoring--logging)
5. [Troubleshooting](#troubleshooting)
6. [Performance Optimization](#performance-optimization)
7. [Security Best Practices](#security-best-practices)

---

## Environment Setup

### Prerequisites

#### System Requirements

| Component | Requirement | Purpose |
|-----------|------------|---------|
| **Operating System** | Linux, macOS, or Windows | Backend runtime |
| **Python** | 3.8 or higher | Backend application |
| **Node.js** | 18+ (for frontend dev) | Frontend build |
| **Disk Space** | 10GB+ free | Document storage |
| **RAM** | 4GB+ recommended | Processing |
| **Network** | Internet connection | AWS Bedrock API |

#### Python Dependencies

```bash
# Core framework
Flask==3.0+
flask-cors==4.0+

# AWS SDK
boto3==latest

# Document processing
PyPDF2==latest
python-docx==latest

# Utilities
python-dotenv==1.0+
```

**Installation**:

```bash
cd semanticSearch
pip install -r requirements.txt
```

**Create requirements.txt** (if not exists):

```txt
Flask>=3.0.0
flask-cors>=4.0.0
boto3>=1.28.0
PyPDF2>=3.0.0
python-docx>=0.8.11
python-dotenv>=1.0.0
```

#### AWS Setup

**Required AWS Services**:
- Amazon Bedrock (Titan Embeddings, Meta Llama 3)
- Amazon Comprehend (optional)

**AWS CLI Configuration**:

```bash
# Install AWS CLI
pip install awscli

# Configure credentials
aws configure
```

**Required Inputs**:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (e.g., `us-east-1`)
- Default output format (e.g., `json`)

**Bedrock Model Access**:

1. Go to AWS Console → Bedrock → Model Access
2. Request access to:
   - Amazon Titan Embed Text v1
   - Meta Llama 3 70B Instruct v1:0
3. Wait for approval (usually instant)

---

## Service Configuration

### Environment Variables

Create `.env` file in `semanticSearch/` directory:

```bash
# ==========================================
# Semantic Search Service Configuration
# ==========================================

# ─────────────────────────────────────────
# Service Settings
# ─────────────────────────────────────────
FLASK_HOST=0.0.0.0
FLASK_PORT=5008
FLASK_DEBUG=False

# ─────────────────────────────────────────
# AWS Configuration
# ─────────────────────────────────────────
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here

# S3 Bucket (for video transcription only)
SEMANTIC_SEARCH_BUCKET=mediagenai-semantic-search

# ─────────────────────────────────────────
# File Upload Limits
# ─────────────────────────────────────────
# Maximum upload file size (bytes) - 500MB default
MAX_CONTENT_LENGTH=524288000

# ─────────────────────────────────────────
# Storage Directories
# ─────────────────────────────────────────
# These are relative to the semanticSearch/ directory
DOCUMENTS_DIR=documents
INDICES_DIR=indices
VIDEOS_DIR=videos

# ─────────────────────────────────────────
# Logging
# ─────────────────────────────────────────
LOG_LEVEL=INFO
LOG_FILE=semantic_search.log
```

### Configuration Loading

The service automatically loads configuration:

```python
from dotenv import load_dotenv
load_dotenv()

# AWS Region
DEFAULT_AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# AWS Clients
rekognition = boto3.client("rekognition", region_name=DEFAULT_AWS_REGION)
transcribe = boto3.client("transcribe", region_name=DEFAULT_AWS_REGION)
comprehend = boto3.client("comprehend", region_name=DEFAULT_AWS_REGION)
bedrock_runtime = boto3.client("bedrock-runtime", region_name=DEFAULT_AWS_REGION)
s3 = boto3.client("s3", region_name=DEFAULT_AWS_REGION)

# File Upload Limit
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
```

### Directory Structure Setup

```bash
cd semanticSearch

# Create required directories
mkdir -p documents
mkdir -p indices
mkdir -p videos

# Set permissions (Linux/macOS)
chmod 755 documents indices videos
```

**Automatic Creation**:

```python
# In app.py
DOCUMENTS_DIR.mkdir(exist_ok=True)
VIDEOS_DIR.mkdir(exist_ok=True)
INDICES_DIR.mkdir(exist_ok=True)
```

---

## Deployment Procedures

### Local Development

#### Start Backend Service

```bash
cd semanticSearch
python app.py
```

**Expected Output**:

```
Loaded 0 videos from index
Loaded 3 documents from index
 * Serving Flask app 'app'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment.
 * Running on http://0.0.0.0:5008
Press CTRL+C to quit
```

#### Start Frontend (Development)

```bash
cd frontend
npm install
npm start
```

Frontend will launch at `http://localhost:3000`

### Production Deployment

#### Using systemd (Linux)

Create service file `/etc/systemd/system/semantic-search.service`:

```ini
[Unit]
Description=Semantic Search Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/mediaGenAI/semanticSearch
Environment="PATH=/opt/mediaGenAI/venv/bin"
ExecStart=/opt/mediaGenAI/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Start service**:

```bash
sudo systemctl enable semantic-search
sudo systemctl start semantic-search
sudo systemctl status semantic-search
```

#### Using Gunicorn (WSGI Server)

**Install Gunicorn**:

```bash
pip install gunicorn
```

**Run with Gunicorn**:

```bash
gunicorn \
  --bind 0.0.0.0:5008 \
  --workers 4 \
  --timeout 300 \
  --access-logfile - \
  --error-logfile - \
  app:app
```

**systemd service with Gunicorn**:

```ini
[Unit]
Description=Semantic Search Service (Gunicorn)
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/opt/mediaGenAI/semanticSearch
Environment="PATH=/opt/mediaGenAI/venv/bin"
ExecStart=/opt/mediaGenAI/venv/bin/gunicorn \
  --bind 0.0.0.0:5008 \
  --workers 4 \
  --timeout 300 \
  app:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

#### Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name search.example.com;

    # Frontend static files
    location / {
        root /var/www/mediagenai/frontend/build;
        try_files $uri /index.html;
    }

    # Backend API proxy
    location /api/search/ {
        proxy_pass http://127.0.0.1:5008/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts for large uploads
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        
        # Large file uploads
        client_max_body_size 500M;
    }
}
```

#### Docker Deployment

**Dockerfile**:

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY semanticSearch/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY semanticSearch/ .

# Create directories
RUN mkdir -p documents indices videos

# Expose port
EXPOSE 5008

# Run service
CMD ["python", "app.py"]
```

**docker-compose.yml**:

```yaml
version: '3.8'

services:
  semantic-search:
    build: .
    ports:
      - "5008:5008"
    volumes:
      - ./documents:/app/documents
      - ./indices:/app/indices
    environment:
      - FLASK_HOST=0.0.0.0
      - FLASK_PORT=5008
      - AWS_REGION=us-east-1
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
    restart: unless-stopped
```

**Run with Docker Compose**:

```bash
docker-compose up -d
docker-compose logs -f semantic-search
```

---

## Monitoring & Logging

### Log Configuration

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('semantic_search.log'),
        logging.StreamHandler()
    ]
)
```

### Log Levels

| Level | Usage |
|-------|-------|
| **DEBUG** | Detailed processing steps |
| **INFO** | Request start/end, uploads, searches |
| **WARNING** | Degraded performance, fallbacks |
| **ERROR** | Processing failures, API errors |

### Key Log Messages

```
INFO: Loaded 3 documents from index
INFO: Job {job_id}: Processing video: {video_title}
INFO: Document saved to: {file_path}
INFO: Searching for: {query}
ERROR: Embedding generation failed: {error}
ERROR: Text extraction failed: {error}
```

### Health Check Endpoint

```bash
curl http://localhost:5008/health
```

**Response**:

```json
{
  "status": "ok",
  "service": "semantic-search",
  "region": "us-east-1"
}
```

### Metrics to Monitor

1. **Request Volume**: Uploads and searches per hour
2. **Processing Time**: Average time per document upload
3. **Success Rate**: Successful uploads / total uploads
4. **Index Size**: Number of indexed documents and chunks
5. **Disk Usage**: Storage consumed by documents
6. **API Latency**: Bedrock API response times

**Recommended Tools**:
- Prometheus + Grafana for metrics
- ELK Stack for log aggregation
- AWS CloudWatch for AWS service metrics

---

## Troubleshooting

### Common Issues

#### 1. AWS Credentials Error

**Symptom**:

```
botocore.exceptions.NoCredentialsError: Unable to locate credentials
```

**Solution**:

```bash
# Option 1: Environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-east-1

# Option 2: AWS CLI configuration
aws configure

# Option 3: .env file
# Add to semanticSearch/.env:
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
```

#### 2. Bedrock Model Access Denied

**Symptom**:

```
botocore.exceptions.ClientError: An error occurred (AccessDeniedException)
when calling the InvokeModel operation
```

**Solution**:

1. Go to AWS Console → Bedrock → Model Access
2. Request access to required models:
   - `amazon.titan-embed-text-v1`
   - `meta.llama3-70b-instruct-v1:0`
3. Wait for approval (usually instant)
4. Verify with AWS CLI:

```bash
aws bedrock list-foundation-models --region us-east-1
```

#### 3. CORS Errors

**Symptom**:

```
Access to fetch at 'http://localhost:5008/upload-document' from origin
'http://localhost:3000' has been blocked by CORS policy
```

**Solution**:

Verify CORS is enabled in `app.py`:

```python
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
```

For specific origins:

```python
CORS(app, origins=["http://localhost:3000", "https://yourdomain.com"])
```

#### 4. File Upload Size Limit

**Symptom**:

```
413 Request Entity Too Large
```

**Solution**:

Increase Flask limit in `app.py`:

```python
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
```

If using Nginx, also update:

```nginx
client_max_body_size 500M;
```

#### 5. PDF Text Extraction Fails

**Symptom**:

```
ERROR: Could not extract text from document
```

**Possible Causes**:
- PDF is image-based (scanned document)
- PDF is password-protected
- PDF is corrupted

**Solution**:

For image-based PDFs, add OCR:

```python
# Install: pip install pytesseract pillow pdf2image
import pytesseract
from pdf2image import convert_from_bytes

def extract_text_with_ocr(file_content):
    images = convert_from_bytes(file_content)
    text_parts = []
    for image in images:
        text = pytesseract.image_to_string(image)
        text_parts.append(text)
    return '\n\n'.join(text_parts)
```

#### 6. Index File Corruption

**Symptom**:

```
ERROR: Error loading document index: JSONDecodeError
```

**Solution**:

Backup and reset index:

```bash
cd semanticSearch/indices

# Backup corrupted index
cp document_index.json document_index.json.backup

# Reset index
echo "[]" > document_index.json

# Restart service
```

**Prevention**: Implement atomic writes:

```python
import tempfile
import shutil

def _save_document_index():
    # Write to temporary file
    with tempfile.NamedTemporaryFile('w', delete=False) as tmp:
        json.dump(DOCUMENT_INDEX, tmp, indent=2, default=str)
        tmp_path = tmp.name
    
    # Atomic rename
    shutil.move(tmp_path, DOCUMENT_INDEX_FILE)
```

#### 7. Memory Issues with Large Documents

**Symptom**:

```
MemoryError: Unable to allocate array
```

**Solution**:

Implement chunked processing:

```python
def process_large_document(file_content, max_chunk_size=100000):
    # Split into smaller chunks for processing
    chunks = []
    for i in range(0, len(file_content), max_chunk_size):
        chunk = file_content[i:i+max_chunk_size]
        processed = process_chunk(chunk)
        chunks.append(processed)
    return chunks
```

---

## Performance Optimization

### Processing Time Optimization

#### 1. Parallel Embedding Generation

```python
from concurrent.futures import ThreadPoolExecutor

def generate_embeddings_parallel(chunks, max_workers=5):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        embeddings = list(executor.map(_generate_embedding, chunks))
    return embeddings
```

**Performance Gain**: ~5x faster for documents with many chunks

#### 2. Caching Embeddings

```python
import hashlib
import json

EMBEDDING_CACHE = {}

def _generate_embedding_cached(text: str) -> List[float]:
    # Create cache key from text hash
    cache_key = hashlib.sha256(text.encode()).hexdigest()
    
    if cache_key in EMBEDDING_CACHE:
        return EMBEDDING_CACHE[cache_key]
    
    embedding = _generate_embedding(text)
    EMBEDDING_CACHE[cache_key] = embedding
    
    return embedding
```

**Benefit**: Avoid redundant API calls for duplicate content

#### 3. Batch Processing

Instead of processing one chunk at a time, batch multiple chunks:

```python
# Note: Titan Embeddings doesn't support batching directly
# But you can optimize by reducing overhead

def upload_document_optimized():
    # ... existing code ...
    
    # Generate all embeddings in one session
    embeddings = []
    for chunk in chunks:
        embedding = _generate_embedding(chunk)
        embeddings.append(embedding)
    
    # Create chunk entries
    chunk_embeddings = [
        {"text": chunk, "embedding": embedding}
        for chunk, embedding in zip(chunks, embeddings)
    ]
```

### Search Performance Optimization

#### 1. Pre-filter Documents

```python
def search_text_optimized():
    # ... existing code ...
    
    # Only search documents matching certain criteria
    relevant_docs = [
        doc for doc in DOCUMENT_INDEX
        if len(doc["chunks"]) > 0  # Has content
    ]
    
    results = []
    for doc in relevant_docs:
        for chunk in doc["chunks"]:
            similarity = _compute_similarity(query_embedding, chunk["embedding"])
            if similarity >= 0.4:  # Pre-filter low scores
                results.append({
                    "document_id": doc["id"],
                    "document_title": doc["title"],
                    "text": chunk["text"],
                    "similarity_score": round(similarity, 4)
                })
```

#### 2. Vector Search Libraries

For large-scale deployments, use specialized vector databases:

```python
# Install: pip install faiss-cpu
import faiss
import numpy as np

# Build FAISS index
def build_faiss_index(embeddings):
    dimension = len(embeddings[0])
    index = faiss.IndexFlatIP(dimension)  # Inner product (cosine sim)
    
    # Normalize embeddings for cosine similarity
    embeddings_np = np.array(embeddings).astype('float32')
    faiss.normalize_L2(embeddings_np)
    
    index.add(embeddings_np)
    return index

# Search with FAISS
def search_with_faiss(query_embedding, index, top_k=5):
    query_np = np.array([query_embedding]).astype('float32')
    faiss.normalize_L2(query_np)
    
    distances, indices = index.search(query_np, top_k)
    return indices[0], distances[0]
```

**Performance Gain**: 10-100x faster for large document collections

### Disk I/O Optimization

#### 1. Reduce Index Writes

```python
# Batch updates instead of saving after each upload
pending_updates = []

def upload_document_batched():
    # ... process document ...
    pending_updates.append(doc_entry)
    
    # Save periodically or on shutdown
    if len(pending_updates) >= 10:
        flush_updates()

def flush_updates():
    DOCUMENT_INDEX.extend(pending_updates)
    _save_document_index()
    pending_updates.clear()
```

#### 2. Compress Index Files

```python
import gzip
import json

def _save_document_index_compressed():
    with gzip.open(f"{DOCUMENT_INDEX_FILE}.gz", 'wt', encoding='utf-8') as f:
        json.dump(DOCUMENT_INDEX, f, indent=2, default=str)

def _load_document_index_compressed():
    global DOCUMENT_INDEX
    if Path(f"{DOCUMENT_INDEX_FILE}.gz").exists():
        with gzip.open(f"{DOCUMENT_INDEX_FILE}.gz", 'rt', encoding='utf-8') as f:
            DOCUMENT_INDEX = json.load(f)
```

**Benefit**: 70-90% size reduction

---

## Security Best Practices

### 1. Input Validation

```python
import re
from werkzeug.utils import secure_filename

def validate_document_upload(doc_file):
    # File type whitelist
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'txt'}
    ext = doc_file.filename.split('.')[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError('Invalid file type')
    
    # File size limit
    MAX_SIZE = 500 * 1024 * 1024  # 500MB
    doc_file.seek(0, os.SEEK_END)
    size = doc_file.tell()
    doc_file.seek(0)
    if size > MAX_SIZE:
        raise ValueError('File too large')
    
    # Secure filename
    safe_filename = secure_filename(doc_file.filename)
    if not safe_filename:
        raise ValueError('Invalid filename')
```

### 2. Rate Limiting

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per hour"]
)

@app.route("/upload-document", methods=["POST"])
@limiter.limit("10 per hour")
def upload_document():
    # ... processing ...

@app.route("/search-text", methods=["POST"])
@limiter.limit("100 per hour")
def search_text():
    # ... processing ...
```

### 3. Authentication (Production)

```python
from functools import wraps
from flask import request, abort

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key not in VALID_API_KEYS:
            abort(401)
        return f(*args, **kwargs)
    return decorated

@app.route("/upload-document", methods=["POST"])
@require_api_key
def upload_document():
    # ... processing ...
```

### 4. AWS IAM Policy (Production)

Minimum required permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v1",
        "arn:aws:bedrock:*::foundation-model/meta.llama3-70b-instruct-v1:0"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "comprehend:DetectKeyPhrases",
        "comprehend:DetectEntities"
      ],
      "Resource": "*"
    }
  ]
}
```

### 5. Document Sanitization

```python
def sanitize_extracted_text(text: str) -> str:
    # Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Limit length
    MAX_LENGTH = 1000000  # 1M characters
    if len(text) > MAX_LENGTH:
        text = text[:MAX_LENGTH]
    
    return text.strip()
```

### 6. Secrets Management

**Use environment variables** instead of hardcoding:

```python
# BAD
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"

# GOOD
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
```

**Use AWS Secrets Manager** for production:

```python
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name=DEFAULT_AWS_REGION)
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# Load credentials
credentials = get_secret("mediagenai/semantic-search/credentials")
```

---

## Backup & Recovery

### Data Backup

```bash
# Backup documents and indices
tar -czf backup_$(date +%Y%m%d).tar.gz \
  semanticSearch/documents \
  semanticSearch/indices

# Upload to S3
aws s3 cp backup_$(date +%Y%m%d).tar.gz \
  s3://your-backup-bucket/semantic-search/
```

### Automated Backup Script

```bash
#!/bin/bash
# backup_semantic_search.sh

BACKUP_DIR="/backups/semantic-search"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.tar.gz"

mkdir -p "$BACKUP_DIR"

cd /opt/mediaGenAI
tar -czf "$BACKUP_FILE" \
  semanticSearch/documents \
  semanticSearch/indices

# Keep only last 30 days
find "$BACKUP_DIR" -type f -mtime +30 -delete

# Upload to S3
aws s3 cp "$BACKUP_FILE" s3://your-backup-bucket/semantic-search/
```

**Schedule with cron**:

```bash
# crontab -e
0 2 * * * /opt/scripts/backup_semantic_search.sh
```

### Disaster Recovery

1. **Index Corruption**: Restore from backup, re-index documents
2. **Service Failure**: Restart from systemd
3. **Data Loss**: Restore from S3 backup

---

## Appendix: Quick Reference

### Service Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/upload-document` | POST | Upload and index document |
| `/documents` | GET | List all documents |
| `/documents/<id>` | DELETE | Delete document |
| `/search-text` | POST | Semantic search |
| `/ask-question` | POST | Q&A about document |
| `/askme` | POST | MediaGenAI documentation chatbot |

### Default Ports

| Service | Port |
|---------|------|
| Semantic Search API | 5008 |
| Frontend (dev) | 3000 |

### File Locations

| Type | Path |
|------|------|
| Documents | `semanticSearch/documents/` |
| Indices | `semanticSearch/indices/` |
| Logs | `semanticSearch/semantic_search.log` |
| Config | `semanticSearch/.env` |

### Command Reference

```bash
# Start service
python app.py

# Start with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5008 app:app

# Check logs
tail -f semantic_search.log

# Test health endpoint
curl http://localhost:5008/health

# Upload document (example)
curl -X POST http://localhost:5008/upload-document \
  -F "document=@sample.pdf" \
  -F "title=Sample Document"

# Search (example)
curl -X POST http://localhost:5008/search-text \
  -H "Content-Type: application/json" \
  -d '{"query": "artificial intelligence", "top_k": 5}'
```

---

## Documentation Complete

This concludes the 4-part Semantic Search Text System Architecture & Logic Guide:

- **Part 1:** System Overview & Architecture
- **Part 2:** API Endpoints & Processing Logic
- **Part 3:** Frontend Architecture & Components
- **Part 4:** Deployment & Operations *(this document)*

For questions or support, contact the MediaGenAI development team.

---

*End of Part 4 — Documentation Series Complete*
