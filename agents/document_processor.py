"""
Document Processor - Main Orchestrator
Coordinates the document parsing agents for comprehensive document analysis
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import hashlib

# Import the agents
from document_text_parser import DocumentTextParser
from document_ocr_agent import DocumentOCRAgent
from table_parser_agent import TableParserAgent


class DocumentProcessor:
    """Main orchestrator for document processing agents"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the document processor
        
        Args:
            config: Configuration options
                - ocr_engine: OCR engine preference ('tesseract', 'easyocr', 'auto')
                - enable_ocr: Enable OCR processing for images
                - enable_tables: Enable table extraction
                - cache_results: Cache processing results
        """
        self.config = config or {}
        
        # Initialize agents
        self.text_parser = DocumentTextParser()
        self.ocr_agent = DocumentOCRAgent(
            ocr_engine=self.config.get('ocr_engine', 'auto')
        ) if self.config.get('enable_ocr', True) else None
        self.table_parser = TableParserAgent() if self.config.get('enable_tables', True) else None
        
        # Cache for processed documents
        self.cache = {} if self.config.get('cache_results', True) else None
        
    def process(self, file_path: str, options: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process a document using appropriate agents
        
        Args:
            file_path: Path to the document
            options: Processing options
                - extract_text: Extract text content
                - extract_tables: Extract table data
                - extract_images: Process embedded images
                - ocr_images: Apply OCR to images
                - extract_metadata: Extract document metadata
                - output_format: Output format ('json', 'text', 'structured')
                
        Returns:
            Comprehensive document analysis results
        """
        options = options or {}
        
        # Check cache
        cache_key = self._get_cache_key(file_path, options)
        if self.cache and cache_key in self.cache:
            return self.cache[cache_key]
        
        result = {
            'file': file_path,
            'timestamp': datetime.now().isoformat(),
            'content': {},
            'metadata': {},
            'statistics': {},
            'errors': []
        }
        
        try:
            path = Path(file_path)
            if not path.exists():
                result['errors'].append(f"File not found: {file_path}")
                return result
            
            file_ext = path.suffix.lower()
            result['metadata']['file_type'] = file_ext
            result['metadata']['file_size'] = path.stat().st_size
            
            # Determine processing strategy
            if self._is_image_file(file_ext):
                result = self._process_image_document(path, options, result)
            elif self._is_text_document(file_ext):
                result = self._process_text_document(path, options, result)
            else:
                result['errors'].append(f"Unsupported file type: {file_ext}")
            
            # Format output
            if options.get('output_format') == 'text':
                result = self._format_as_text(result)
            elif options.get('output_format') == 'structured':
                result = self._format_as_structured(result)
            
            # Cache result
            if self.cache:
                self.cache[cache_key] = result
                
        except Exception as e:
            result['errors'].append(f"Processing error: {str(e)}")
        
        return result
    
    def _is_image_file(self, ext: str) -> bool:
        """Check if file is an image"""
        return ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif']
    
    def _is_text_document(self, ext: str) -> bool:
        """Check if file is a text-based document"""
        return ext in ['.pdf', '.docx', '.doc', '.txt', '.html', '.xml', '.csv', '.xlsx', '.xls', '.pptx', '.ppt', '.md', '.json']
    
    def _process_image_document(self, path: Path, options: Dict, result: Dict) -> Dict:
        """Process image documents"""
        if self.ocr_agent and options.get('ocr_images', True):
            ocr_options = {
                'preprocess': options.get('ocr_preprocess', True),
                'detect_layout': options.get('detect_layout', False),
                'confidence_threshold': options.get('confidence_threshold', 50)
            }
            
            ocr_result = self.ocr_agent.process_document(str(path), ocr_options)
            
            result['content']['ocr_text'] = ocr_result.get('text', '')
            result['content']['text_blocks'] = ocr_result.get('blocks', [])
            result['metadata']['ocr_confidence'] = ocr_result.get('confidence', 0)
            
            if ocr_result.get('layout'):
                result['content']['layout'] = ocr_result['layout']
            
            if ocr_result.get('errors'):
                result['errors'].extend(ocr_result['errors'])
            
            # Extract tables from OCR text if enabled
            if self.table_parser and options.get('extract_tables', True) and ocr_result.get('text'):
                table_result = self.table_parser.parse_tables(
                    ocr_result['text'],
                    source_type='text'
                )
                if table_result.get('tables'):
                    result['content']['tables'] = table_result['tables']
        else:
            result['errors'].append("OCR not enabled or not available for image processing")
        
        return result
    
    def _process_text_document(self, path: Path, options: Dict, result: Dict) -> Dict:
        """Process text-based documents"""
        
        # Extract text content
        if options.get('extract_text', True):
            text_options = {
                'extract_metadata': options.get('extract_metadata', True),
                'clean_text': options.get('clean_text', False),
                'max_pages': options.get('max_pages')
            }
            
            text_result = self.text_parser.parse(str(path), text_options)
            
            result['content']['text'] = text_result.get('text', '')
            result['metadata'].update(text_result.get('metadata', {}))
            
            if text_result.get('structure'):
                result['content']['structure'] = text_result['structure']
            
            if text_result.get('errors'):
                result['errors'].extend(text_result['errors'])
            
            # Get text statistics
            if text_result.get('text'):
                result['statistics'] = self.text_parser.get_statistics(text_result['text'])
        
        # Extract tables
        if self.table_parser and options.get('extract_tables', True):
            table_options = {
                'pages': options.get('table_pages', 'all'),
                'encoding': options.get('encoding', 'utf-8')
            }
            
            table_result = self.table_parser.parse_tables(str(path), source_type='auto', options=table_options)
            
            if table_result.get('tables'):
                result['content']['tables'] = table_result['tables']
                result['statistics']['table_count'] = len(table_result['tables'])
                result['statistics']['table_statistics'] = table_result.get('statistics', {})
            
            if table_result.get('errors'):
                result['errors'].extend(table_result['errors'])
        
        # Process embedded images in PDFs
        if path.suffix.lower() == '.pdf' and options.get('extract_images', False):
            result['content']['embedded_images'] = self._extract_pdf_images(path)
        
        return result
    
    def _extract_pdf_images(self, path: Path) -> List[Dict]:
        """Extract embedded images from PDF (placeholder for full implementation)"""
        # This would require additional libraries like PyMuPDF or pdf2image
        # For now, return empty list
        return []
    
    def _get_cache_key(self, file_path: str, options: Dict) -> str:
        """Generate cache key for a document and options"""
        key_data = f"{file_path}_{json.dumps(options, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _format_as_text(self, result: Dict) -> Dict:
        """Format result as plain text"""
        text_output = []
        
        if result.get('content', {}).get('text'):
            text_output.append(result['content']['text'])
        
        if result.get('content', {}).get('ocr_text'):
            text_output.append("\n--- OCR Text ---\n")
            text_output.append(result['content']['ocr_text'])
        
        if result.get('content', {}).get('tables'):
            text_output.append("\n--- Tables ---\n")
            for table in result['content']['tables']:
                text_output.append(f"Table: {table.get('id', 'unknown')}")
                if table.get('data'):
                    for row in table['data']:
                        text_output.append(str(row))
        
        result['formatted_output'] = '\n'.join(text_output)
        return result
    
    def _format_as_structured(self, result: Dict) -> Dict:
        """Format result as structured data"""
        structured = {
            'summary': {
                'file': result.get('file'),
                'type': result.get('metadata', {}).get('file_type'),
                'size': result.get('metadata', {}).get('file_size'),
                'text_length': len(result.get('content', {}).get('text', '')),
                'tables_found': len(result.get('content', {}).get('tables', [])),
                'errors': len(result.get('errors', []))
            },
            'content': result.get('content', {}),
            'metadata': result.get('metadata', {}),
            'statistics': result.get('statistics', {})
        }
        
        result['structured_output'] = structured
        return result
    
    def batch_process(self, file_paths: List[str], options: Optional[Dict] = None) -> List[Dict]:
        """Process multiple documents"""
        results = []
        
        for file_path in file_paths:
            result = self.process(file_path, options)
            results.append(result)
        
        return results
    
    def process_directory(self, directory: str, pattern: str = "*", options: Optional[Dict] = None) -> List[Dict]:
        """Process all matching documents in a directory"""
        dir_path = Path(directory)
        if not dir_path.is_dir():
            return []
        
        files = list(dir_path.glob(pattern))
        return self.batch_process([str(f) for f in files if f.is_file()], options)
    
    def compare_documents(self, file1: str, file2: str) -> Dict:
        """Compare two documents"""
        doc1 = self.process(file1, {'extract_text': True, 'extract_tables': True})
        doc2 = self.process(file2, {'extract_text': True, 'extract_tables': True})
        
        comparison = {
            'file1': file1,
            'file2': file2,
            'text_similarity': self._calculate_text_similarity(
                doc1.get('content', {}).get('text', ''),
                doc2.get('content', {}).get('text', '')
            ),
            'structure_comparison': {
                'file1_tables': len(doc1.get('content', {}).get('tables', [])),
                'file2_tables': len(doc2.get('content', {}).get('tables', [])),
                'file1_words': doc1.get('statistics', {}).get('words', 0),
                'file2_words': doc2.get('statistics', {}).get('words', 0)
            }
        }
        
        return comparison
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate basic text similarity (Jaccard similarity)"""
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def export_results(self, result: Dict, output_path: str, format: str = 'json') -> bool:
        """Export processing results to file"""
        try:
            if format == 'json':
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False, default=str)
            elif format == 'text':
                formatted = self._format_as_text(result)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(formatted.get('formatted_output', ''))
            else:
                return False
            
            return True
        except Exception as e:
            return False
    
    def get_supported_formats(self) -> Dict:
        """Get information about supported formats"""
        return {
            'text_documents': self.text_parser.supported_formats if self.text_parser else [],
            'image_formats': ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif'] if self.ocr_agent else [],
            'table_parsers': self.table_parser.available_parsers if self.table_parser else [],
            'ocr_engine': self.ocr_agent.ocr_engine if self.ocr_agent else None
        }


if __name__ == "__main__":
    # Example usage
    import sys
    
    # Initialize processor
    processor = DocumentProcessor({
        'enable_ocr': True,
        'enable_tables': True,
        'cache_results': True
    })
    
    # Show supported formats
    print("Supported formats:")
    formats = processor.get_supported_formats()
    for key, value in formats.items():
        print(f"  {key}: {value}")
    
    # Process document if provided
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        
        print(f"\nProcessing: {file_path}")
        
        result = processor.process(file_path, {
            'extract_text': True,
            'extract_tables': True,
            'extract_metadata': True,
            'ocr_images': True,
            'output_format': 'structured'
        })
        
        if result.get('structured_output'):
            summary = result['structured_output']['summary']
            print(f"\nSummary:")
            print(f"  File type: {summary.get('type')}")
            print(f"  File size: {summary.get('size')} bytes")
            print(f"  Text length: {summary.get('text_length')} characters")
            print(f"  Tables found: {summary.get('tables_found')}")
            print(f"  Errors: {summary.get('errors')}")
        
        if result.get('errors'):
            print(f"\nErrors encountered:")
            for error in result['errors']:
                print(f"  - {error}")
        
        # Export results
        output_file = file_path + '_analysis.json'
        if processor.export_results(result, output_file, 'json'):
            print(f"\nResults exported to: {output_file}")