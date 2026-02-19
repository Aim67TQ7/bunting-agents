# Overview

This is a Flask-based web application called the Contract Analysis Tool that helps sellers analyze buyer-supplied contracts against their baseline terms and conditions. The tool extracts text from various document formats (PDF, DOCX, images), processes them using OpenAI's API, and generates compliance reports with scoring and recommendations.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Web Framework
- **Flask**: Lightweight web framework chosen for rapid development and simplicity
- **Jinja2 Templates**: Server-side rendering for HTML pages with Bootstrap CSS framework
- **Static Assets**: CSS and JavaScript files for frontend styling and basic form validation

## Document Processing Pipeline
- **Multi-format Support**: Handles PDF (pdfplumber, pypdf), DOCX (python-docx), text files, and images
- **OCR Fallback**: Uses Tesseract OCR with pdf2image for image-based documents and scanned PDFs
- **Text Chunking**: Implements tiktoken for intelligent text segmentation to fit LLM context windows
- **File Validation**: Enforces file type restrictions and 16MB size limits

## 3-Agent Analysis System
- **Agent 1 (Parser)**: Document parsing and metadata extraction (agent1_parser.py)
  - Extracts text from uploaded files
  - Detects Bunting seller documents vs buyer contracts
  - Extracts basic metadata, party information, and line items
  - Routes to appropriate next agent based on document type
- **Agent 2 (Risk Analyzer)**: Risk analysis and clause comparison (agent2_risk.py)
  - Analyzes buyer contracts for contradictions with seller baseline
  - Focuses only on direct conflicts, not missing terms
  - Generates severity ratings (HIGH/MEDIUM/LOW) with color coding
  - Calculates compliance scores based on detected contradictions
- **Agent 3 (Report Generator)**: Final report generation and scoring (agent3_report.py)
  - Creates structured AnalysisResult objects from agent data
  - Generates JSON, Markdown, and XML reports for download
  - Handles both seller document parsing and buyer risk analysis results

## AI Analysis Engine
- **OpenAI Integration**: Uses OpenAI's API with GPT models for contract analysis
- **Structured Output**: Pydantic models ensure consistent JSON schema for analysis results
- **Baseline Comparison**: Compares uploaded contracts against predefined seller terms stored in Markdown format
- **Simplified Contradiction Analysis**: Shows only direct conflicts with color-coded severity ratings
- **Bunting Document Detection**: Automatically identifies seller documents for customer/line item parsing

## File Management
- **Upload Handling**: Secure file uploads with werkzeug's secure_filename function
- **Temporary Storage**: Uses uploads/ and reports/ directories for file processing
- **Report Generation**: Creates both JSON and Markdown reports for download

## Security Measures
- **Input Validation**: File type and size restrictions prevent malicious uploads
- **Secure Filenames**: Sanitizes uploaded filenames to prevent directory traversal
- **Session Management**: Uses Flask's built-in session handling with configurable secret keys
- **Proxy Handling**: ProxyFix middleware for proper header handling behind reverse proxies

## Configuration Management
- **Environment Variables**: Uses environment variables for sensitive configuration (API keys, session secrets)
- **Default Fallbacks**: Provides sensible defaults for development environments
- **Directory Creation**: Automatically creates required upload and report directories

# External Dependencies

## AI Services
- **OpenAI API**: Core dependency for contract analysis using GPT models, requires API key configuration

## Document Processing Libraries
- **pypdf & pdfplumber**: PDF text extraction with fallback options
- **python-docx**: Microsoft Word document processing
- **Pillow & pytesseract**: Image processing and OCR capabilities
- **pdf2image**: PDF to image conversion for OCR processing

## System Dependencies
- **Tesseract OCR**: System-level OCR engine for image text extraction
- **Poppler**: PDF rendering utilities required by pdf2image

## Text Processing
- **tiktoken**: OpenAI's tokenizer for accurate text chunking and token counting
- **pydantic**: Data validation and schema enforcement for structured outputs

## Web Framework Stack
- **Flask**: Web application framework
- **werkzeug**: WSGI utilities and security helpers
- **Bootstrap CSS**: Frontend styling framework via CDN
- **Font Awesome**: Icon library for UI elements

## Development Tools
- **logging**: Built-in Python logging for debugging and monitoring
- **tempfile**: Temporary file handling for processing workflows