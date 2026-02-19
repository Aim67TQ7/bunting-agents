# Document Processing Agents

A comprehensive document processing system with three specialized agents for parsing various document formats.

## Features

### 1. **Document Text Parser Agent** (`document_text_parser.py`)
- Extracts text from multiple document formats
- Supported formats: PDF, Word, Excel, PowerPoint, HTML, XML, JSON, CSV, Markdown, plain text
- Features:
  - Metadata extraction
  - Document structure analysis
  - Text cleaning and normalization
  - Section extraction
  - Text statistics

### 2. **Document OCR Agent** (`document_ocr_agent.py`)
- Performs optical character recognition on images
- Supported OCR engines: Tesseract, EasyOCR
- Features:
  - Image preprocessing (deskew, denoise, contrast enhancement)
  - Layout detection
  - Text block extraction with confidence scores
  - Table detection in images
  - Batch processing

### 3. **Table Parser Agent** (`table_parser_agent.py`)
- Extracts structured table data from documents
- Supported sources: PDF, HTML, Excel, CSV, plain text
- Features:
  - Multiple parsing engines (Camelot, Tabula, pandas)
  - Automatic delimiter detection
  - Data type detection
  - Table validation and cleaning
  - Export to multiple formats (CSV, JSON, Excel, Markdown)

### 4. **Document Processor** (`document_processor.py`)
- Main orchestrator that coordinates all agents
- Intelligent document type detection
- Comprehensive document analysis
- Result caching
- Batch processing

## Installation

```bash
# Install basic requirements
pip install -r requirements.txt

# For OCR support (optional):
# Install Tesseract OCR
# Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
# Linux: sudo apt-get install tesseract-ocr
# Mac: brew install tesseract

# For advanced PDF table extraction (optional):
# Install Ghostscript for Camelot
# Windows: Download from https://www.ghostscript.com/download/gsdnld.html
# Linux: sudo apt-get install ghostscript
# Mac: brew install ghostscript
```

## Quick Start

### Basic Usage

```python
from document_processor import DocumentProcessor

# Initialize the processor
processor = DocumentProcessor({
    'enable_ocr': True,
    'enable_tables': True,
    'cache_results': True
})

# Process a document
result = processor.process('document.pdf', {
    'extract_text': True,
    'extract_tables': True,
    'extract_metadata': True,
    'output_format': 'structured'
})

# Access the results
print(f"Text extracted: {len(result['content']['text'])} characters")
print(f"Tables found: {len(result['content'].get('tables', []))}")
print(f"Metadata: {result['metadata']}")
```

### Using Individual Agents

#### Text Parser
```python
from document_text_parser import DocumentTextParser

parser = DocumentTextParser()
result = parser.parse('document.docx', {
    'extract_metadata': True,
    'clean_text': True
})
print(result['text'])
```

#### OCR Agent
```python
from document_ocr_agent import DocumentOCRAgent

ocr = DocumentOCRAgent(ocr_engine='auto')
result = ocr.process_document('image.png', {
    'preprocess': True,
    'detect_layout': True
})
print(f"OCR Text: {result['text']}")
print(f"Confidence: {result['confidence']}%")
```

#### Table Parser
```python
from table_parser_agent import TableParserAgent

table_parser = TableParserAgent()
result = table_parser.parse_tables('data.pdf', source_type='pdf')
for table in result['tables']:
    print(f"Table {table['id']}: {table['rows']} rows x {table['columns']} columns")
```

## Processing Options

### Document Processor Options
- `extract_text`: Extract text content (default: True)
- `extract_tables`: Extract table data (default: True)
- `extract_images`: Process embedded images (default: False)
- `ocr_images`: Apply OCR to images (default: True)
- `extract_metadata`: Extract document metadata (default: True)
- `output_format`: 'json', 'text', or 'structured'

### OCR Options
- `preprocess`: Apply image preprocessing (default: True)
- `deskew`: Correct image skew
- `denoise`: Remove noise from image
- `enhance_contrast`: Enhance image contrast
- `detect_layout`: Detect document layout structure
- `confidence_threshold`: Minimum confidence for text (default: 50)

### Table Parsing Options
- `pages`: Page numbers for PDF ('all' or list of numbers)
- `area`: Coordinates for table area in PDF
- `columns`: Column separator for text tables
- `header_row`: Row index for headers
- `skip_rows`: Number of rows to skip

## Command Line Usage

Each agent can be run from the command line:

```bash
# Process any document with the main processor
python document_processor.py document.pdf

# Parse text from a document
python document_text_parser.py document.docx

# Perform OCR on an image
python document_ocr_agent.py image.png

# Extract tables from a document
python table_parser_agent.py data.pdf
```

## Batch Processing

```python
# Process multiple documents
results = processor.batch_process(['doc1.pdf', 'doc2.docx', 'doc3.html'])

# Process entire directory
results = processor.process_directory('/path/to/documents', pattern='*.pdf')
```

## Export Results

```python
# Export to JSON
processor.export_results(result, 'output.json', format='json')

# Export tables to CSV
table_parser.export_tables(tables, 'csv', 'tables.csv')

# Export tables to Excel
table_parser.export_tables(tables, 'excel', 'tables.xlsx')
```

## Document Comparison

```python
comparison = processor.compare_documents('doc1.pdf', 'doc2.pdf')
print(f"Text similarity: {comparison['text_similarity']:.2%}")
```

## Supported Formats

### Text Documents
- PDF (.pdf)
- Microsoft Word (.docx, .doc)
- Microsoft Excel (.xlsx, .xls)
- Microsoft PowerPoint (.pptx, .ppt)
- HTML (.html, .htm)
- XML (.xml)
- JSON (.json)
- CSV (.csv)
- Markdown (.md)
- Plain text (.txt, .log)

### Images (with OCR)
- PNG (.png)
- JPEG (.jpg, .jpeg)
- GIF (.gif)
- BMP (.bmp)
- TIFF (.tiff, .tif)

## Performance Tips

1. **Enable caching** for repeated document processing
2. **Use batch processing** for multiple documents
3. **Limit pages** when processing large PDFs
4. **Preprocess images** for better OCR accuracy
5. **Choose appropriate OCR engine**:
   - EasyOCR: Better for multiple languages, slower
   - Tesseract: Faster, good for English

## Error Handling

The system provides detailed error information:

```python
result = processor.process('document.pdf')
if result['errors']:
    for error in result['errors']:
        print(f"Error: {error}")
```

## Requirements

See `requirements.txt` for full list. Key dependencies:
- **Required**: Pillow, numpy
- **Document parsing**: PyPDF2, python-docx, openpyxl, beautifulsoup4
- **OCR (optional)**: pytesseract, easyocr, opencv-python
- **Tables (optional)**: pandas, tabula-py, camelot-py

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit pull requests.

## Troubleshooting

### OCR not working
- Ensure Tesseract is installed and in PATH
- For EasyOCR, first run may download models (~60-200MB)

### PDF table extraction issues
- Install Ghostscript for Camelot
- Try different parser (tabula vs camelot)
- Adjust area coordinates for specific tables

### Memory issues with large files
- Use `max_pages` option for PDFs
- Process files in batches
- Disable caching for very large datasets