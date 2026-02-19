"""
Example usage of the Document Processing Agents
"""

from document_processor import DocumentProcessor
from document_text_parser import DocumentTextParser
from document_ocr_agent import DocumentOCRAgent
from table_parser_agent import TableParserAgent
import json


def example_basic_processing():
    """Basic document processing example"""
    print("=" * 50)
    print("BASIC DOCUMENT PROCESSING")
    print("=" * 50)
    
    # Initialize processor
    processor = DocumentProcessor({
        'enable_ocr': True,
        'enable_tables': True,
        'cache_results': True
    })
    
    # Example: Process a PDF document
    # Replace with your actual file path
    file_path = "sample_document.pdf"
    
    try:
        result = processor.process(file_path, {
            'extract_text': True,
            'extract_tables': True,
            'extract_metadata': True,
            'clean_text': True,
            'output_format': 'structured'
        })
        
        if result.get('structured_output'):
            summary = result['structured_output']['summary']
            print(f"\nDocument: {summary['file']}")
            print(f"Type: {summary['type']}")
            print(f"Size: {summary['size']} bytes")
            print(f"Text length: {summary['text_length']} characters")
            print(f"Tables found: {summary['tables_found']}")
            
            # Show first 200 characters of text
            text = result.get('content', {}).get('text', '')
            if text:
                print(f"\nFirst 200 characters of text:")
                print(text[:200] + "..." if len(text) > 200 else text)
        
        if result.get('errors'):
            print("\nNote: Some errors occurred during processing:")
            for error in result['errors']:
                print(f"  - {error}")
    
    except Exception as e:
        print(f"Could not process file: {e}")
        print("Please provide a valid document file path")


def example_text_parsing():
    """Text parsing example"""
    print("\n" + "=" * 50)
    print("TEXT PARSING EXAMPLE")
    print("=" * 50)
    
    parser = DocumentTextParser()
    
    # Create a sample text file for demonstration
    sample_text = """
    # Sample Document
    
    This is a sample document for testing the text parser.
    
    ## Introduction
    The document parser can extract text from various formats including:
    - PDF files
    - Word documents
    - Excel spreadsheets
    - PowerPoint presentations
    
    ## Features
    1. Metadata extraction
    2. Structure analysis
    3. Text statistics
    """
    
    # Save sample text
    with open('sample.md', 'w') as f:
        f.write(sample_text)
    
    # Parse the document
    result = parser.parse('sample.md', {
        'extract_metadata': True,
        'clean_text': False
    })
    
    print(f"\nParsed Markdown Document:")
    print(f"Text length: {len(result['text'])} characters")
    print(f"Metadata: {result['metadata']}")
    
    # Extract sections
    sections = parser.extract_sections(result['text'])
    print(f"Sections found: {list(sections.keys())}")
    
    # Get statistics
    stats = parser.get_statistics(result['text'])
    print(f"Statistics: {stats}")


def example_ocr_processing():
    """OCR processing example"""
    print("\n" + "=" * 50)
    print("OCR PROCESSING EXAMPLE")
    print("=" * 50)
    
    ocr = DocumentOCRAgent(ocr_engine='auto')
    
    if ocr.ocr_engine:
        print(f"OCR Engine available: {ocr.ocr_engine}")
        
        # For demonstration, we'll create a simple test
        # In real use, provide an actual image file
        image_path = "sample_image.png"
        
        try:
            result = ocr.process_document(image_path, {
                'preprocess': True,
                'enhance_contrast': True,
                'detect_layout': True,
                'confidence_threshold': 50
            })
            
            print(f"\nOCR Results:")
            print(f"Text extracted: {len(result['text'])} characters")
            print(f"Confidence: {result['confidence']:.2f}%")
            print(f"Text blocks found: {len(result['blocks'])}")
            
            if result.get('layout'):
                layout = result['layout']
                print(f"Layout: {layout['columns']} column(s), {layout['orientation']}")
            
            # Show first few text blocks
            if result['blocks']:
                print("\nFirst 3 text blocks:")
                for block in result['blocks'][:3]:
                    print(f"  - '{block['text']}' (confidence: {block['confidence']}%)")
        
        except Exception as e:
            print(f"Could not process image: {e}")
            print("Please provide a valid image file for OCR")
    else:
        print("No OCR engine available. Install pytesseract or easyocr.")


def example_table_extraction():
    """Table extraction example"""
    print("\n" + "=" * 50)
    print("TABLE EXTRACTION EXAMPLE")
    print("=" * 50)
    
    table_parser = TableParserAgent()
    
    # Create a sample CSV for demonstration
    sample_csv = """Name,Age,Department,Salary
John Doe,30,Engineering,75000
Jane Smith,28,Marketing,65000
Bob Johnson,35,Sales,70000
Alice Brown,32,HR,60000"""
    
    with open('sample_table.csv', 'w') as f:
        f.write(sample_csv)
    
    # Parse the table
    result = table_parser.parse_tables('sample_table.csv', source_type='csv')
    
    print(f"\nTables found: {len(result['tables'])}")
    
    for table in result['tables']:
        print(f"\nTable ID: {table['id']}")
        print(f"Rows: {table['rows']}")
        print(f"Columns: {table['columns']}")
        print(f"Headers: {table['headers']}")
        
        # Show data
        print("\nTable data:")
        for row in table['data']:
            print(f"  {row}")
    
    # Export to different formats
    print("\nExporting tables to different formats...")
    table_parser.export_tables(result['tables'], 'json', 'output_table.json')
    table_parser.export_tables(result['tables'], 'markdown', 'output_table.md')
    print("Tables exported to output_table.json and output_table.md")
    
    # Validate table structure
    if result['tables']:
        validation = table_parser.validate_table_structure(result['tables'][0])
        print(f"\nTable validation: {'Valid' if validation['is_valid'] else 'Invalid'}")
        if validation['issues']:
            print(f"Issues: {validation['issues']}")


def example_batch_processing():
    """Batch processing example"""
    print("\n" + "=" * 50)
    print("BATCH PROCESSING EXAMPLE")
    print("=" * 50)
    
    processor = DocumentProcessor()
    
    # Create sample files for demonstration
    files = []
    for i in range(3):
        filename = f'sample_{i+1}.txt'
        with open(filename, 'w') as f:
            f.write(f"This is sample document {i+1}\nIt contains some text for processing.")
        files.append(filename)
    
    # Batch process files
    results = processor.batch_process(files, {
        'extract_text': True,
        'extract_metadata': True
    })
    
    print(f"\nProcessed {len(results)} documents:")
    for result in results:
        print(f"  - {result['file']}: {len(result.get('content', {}).get('text', ''))} characters")


def example_document_comparison():
    """Document comparison example"""
    print("\n" + "=" * 50)
    print("DOCUMENT COMPARISON EXAMPLE")
    print("=" * 50)
    
    processor = DocumentProcessor()
    
    # Create two sample documents
    doc1_content = "This is the first document. It contains information about Python programming and data analysis."
    doc2_content = "This is the second document. It also contains information about Python but focuses on web development."
    
    with open('doc1.txt', 'w') as f:
        f.write(doc1_content)
    
    with open('doc2.txt', 'w') as f:
        f.write(doc2_content)
    
    # Compare documents
    comparison = processor.compare_documents('doc1.txt', 'doc2.txt')
    
    print(f"\nDocument Comparison:")
    print(f"File 1: {comparison['file1']}")
    print(f"File 2: {comparison['file2']}")
    print(f"Text similarity: {comparison['text_similarity']:.2%}")
    print(f"Structure comparison: {comparison['structure_comparison']}")


def example_html_table_parsing():
    """HTML table parsing example"""
    print("\n" + "=" * 50)
    print("HTML TABLE PARSING EXAMPLE")
    print("=" * 50)
    
    table_parser = TableParserAgent()
    
    # Create sample HTML with tables
    html_content = """
    <html>
    <body>
        <h1>Sales Report</h1>
        <table>
            <thead>
                <tr>
                    <th>Product</th>
                    <th>Q1 Sales</th>
                    <th>Q2 Sales</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Widget A</td>
                    <td>$10,000</td>
                    <td>$15,000</td>
                    <td>$25,000</td>
                </tr>
                <tr>
                    <td>Widget B</td>
                    <td>$8,000</td>
                    <td>$12,000</td>
                    <td>$20,000</td>
                </tr>
            </tbody>
        </table>
        
        <h2>Employee Data</h2>
        <table>
            <tr>
                <th>Name</th>
                <th>Department</th>
            </tr>
            <tr>
                <td>John</td>
                <td>Sales</td>
            </tr>
            <tr>
                <td>Jane</td>
                <td>Marketing</td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    with open('sample.html', 'w') as f:
        f.write(html_content)
    
    # Parse HTML tables
    result = table_parser.parse_tables('sample.html', source_type='html')
    
    print(f"\nHTML Tables found: {len(result['tables'])}")
    
    for i, table in enumerate(result['tables']):
        print(f"\n{table['id']}:")
        print(f"  Headers: {table['headers']}")
        print(f"  Rows: {table['rows']}")
        print("  Data:")
        for row in table['data']:
            print(f"    {row}")


def main():
    """Run all examples"""
    print("\n" + "=" * 70)
    print("DOCUMENT PROCESSING AGENTS - EXAMPLES")
    print("=" * 70)
    
    # Show available capabilities
    processor = DocumentProcessor()
    formats = processor.get_supported_formats()
    
    print("\nSupported Capabilities:")
    print(f"Text documents: {', '.join(formats['text_documents'])}")
    print(f"Image formats: {', '.join(formats['image_formats'])}")
    print(f"Table parsers: {', '.join(formats['table_parsers'])}")
    print(f"OCR engine: {formats['ocr_engine']}")
    
    # Run examples
    example_basic_processing()
    example_text_parsing()
    example_ocr_processing()
    example_table_extraction()
    example_batch_processing()
    example_document_comparison()
    example_html_table_parsing()
    
    print("\n" + "=" * 70)
    print("EXAMPLES COMPLETED")
    print("=" * 70)
    print("\nNote: Some examples may show errors if sample files don't exist.")
    print("Replace sample file paths with your actual documents for real usage.")


if __name__ == "__main__":
    main()