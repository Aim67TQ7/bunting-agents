"""
Table Parser Agent
Extracts and processes structured table data from documents
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import csv
from io import StringIO

# Table parsing libraries
try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import tabula
except ImportError:
    tabula = None

try:
    import camelot
except ImportError:
    camelot = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


class TableParserAgent:
    """Agent for extracting and parsing table data from documents"""
    
    def __init__(self):
        self.available_parsers = self._check_available_parsers()
    
    def _check_available_parsers(self) -> List[str]:
        """Check which table parsing libraries are available"""
        parsers = ['text']  # Basic text parsing always available
        
        if pd:
            parsers.append('pandas')
        if tabula:
            parsers.append('tabula')
        if camelot:
            parsers.append('camelot')
        if BeautifulSoup:
            parsers.append('html')
            
        return parsers
    
    def parse_tables(self, source: str, source_type: str = 'auto', options: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Parse tables from various sources
        
        Args:
            source: File path or text content
            source_type: Type of source ('pdf', 'html', 'text', 'excel', 'csv', 'auto')
            options: Parsing options
                - pages: Page numbers for PDF (e.g., [1, 2, 3] or 'all')
                - area: Coordinates for table area in PDF
                - columns: Column separator for text tables
                - header_row: Row index for headers
                - skip_rows: Number of rows to skip
                - encoding: Text encoding
                
        Returns:
            Dictionary containing:
                - tables: List of parsed tables
                - metadata: Table metadata
                - statistics: Table statistics
                - errors: Any parsing errors
        """
        options = options or {}
        result = {
            'tables': [],
            'metadata': {},
            'statistics': {},
            'errors': []
        }
        
        try:
            # Detect source type if auto
            if source_type == 'auto':
                source_type = self._detect_source_type(source)
            
            # Parse based on source type
            if source_type == 'pdf':
                result = self._parse_pdf_tables(source, options)
            elif source_type == 'html':
                result = self._parse_html_tables(source, options)
            elif source_type == 'excel':
                result = self._parse_excel_tables(source, options)
            elif source_type == 'csv':
                result = self._parse_csv_table(source, options)
            elif source_type == 'text':
                result = self._parse_text_tables(source, options)
            else:
                result['errors'].append(f"Unsupported source type: {source_type}")
            
            # Calculate statistics for all tables
            if result['tables']:
                result['statistics'] = self._calculate_statistics(result['tables'])
            
        except Exception as e:
            result['errors'].append(f"Table parsing error: {str(e)}")
        
        return result
    
    def _detect_source_type(self, source: str) -> str:
        """Detect the type of source"""
        # Check if it's a file path
        if len(source) < 500 and not '\n' in source:
            path = Path(source)
            if path.exists():
                ext = path.suffix.lower()
                if ext == '.pdf':
                    return 'pdf'
                elif ext in ['.html', '.htm']:
                    return 'html'
                elif ext in ['.xlsx', '.xls']:
                    return 'excel'
                elif ext == '.csv':
                    return 'csv'
        
        # Check if it's HTML content
        if '<table' in source.lower():
            return 'html'
        
        # Default to text
        return 'text'
    
    def _parse_pdf_tables(self, file_path: str, options: Dict) -> Dict:
        """Parse tables from PDF files"""
        result = {
            'tables': [],
            'metadata': {'source': 'pdf'},
            'errors': []
        }
        
        # Try Camelot first (better for complex tables)
        if camelot and 'camelot' in self.available_parsers:
            try:
                pages = options.get('pages', 'all')
                if isinstance(pages, list):
                    pages = ','.join(map(str, pages))
                
                tables = camelot.read_pdf(file_path, pages=pages, flavor='lattice')
                
                for i, table in enumerate(tables):
                    table_data = {
                        'id': f'table_{i+1}',
                        'data': table.df.to_dict('records'),
                        'headers': list(table.df.columns),
                        'rows': len(table.df),
                        'columns': len(table.df.columns),
                        'accuracy': table.accuracy,
                        'page': table.page
                    }
                    result['tables'].append(table_data)
                
                result['metadata']['parser'] = 'camelot'
                return result
                
            except Exception as e:
                result['errors'].append(f"Camelot error: {str(e)}")
        
        # Try Tabula as fallback
        if tabula and 'tabula' in self.available_parsers:
            try:
                pages = options.get('pages', 'all')
                tables = tabula.read_pdf(file_path, pages=pages, multiple_tables=True)
                
                for i, df in enumerate(tables):
                    table_data = {
                        'id': f'table_{i+1}',
                        'data': df.to_dict('records'),
                        'headers': list(df.columns),
                        'rows': len(df),
                        'columns': len(df.columns)
                    }
                    result['tables'].append(table_data)
                
                result['metadata']['parser'] = 'tabula'
                return result
                
            except Exception as e:
                result['errors'].append(f"Tabula error: {str(e)}")
        
        if not result['tables']:
            result['errors'].append("No PDF table parser available. Install camelot-py or tabula-py.")
        
        return result
    
    def _parse_html_tables(self, source: str, options: Dict) -> Dict:
        """Parse tables from HTML content"""
        result = {
            'tables': [],
            'metadata': {'source': 'html'},
            'errors': []
        }
        
        if not BeautifulSoup:
            result['errors'].append("BeautifulSoup not installed")
            return result
        
        try:
            # Check if source is file path or HTML content
            if Path(source).exists():
                with open(source, 'r', encoding=options.get('encoding', 'utf-8')) as f:
                    html_content = f.read()
            else:
                html_content = source
            
            soup = BeautifulSoup(html_content, 'html.parser')
            tables = soup.find_all('table')
            
            for i, table in enumerate(tables):
                table_data = self._parse_html_table_element(table, i)
                if table_data:
                    result['tables'].append(table_data)
            
            result['metadata']['table_count'] = len(result['tables'])
            
        except Exception as e:
            result['errors'].append(f"HTML parsing error: {str(e)}")
        
        return result
    
    def _parse_html_table_element(self, table, index: int) -> Optional[Dict]:
        """Parse a single HTML table element"""
        try:
            headers = []
            rows = []
            
            # Extract headers
            thead = table.find('thead')
            if thead:
                header_row = thead.find('tr')
                if header_row:
                    headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
            else:
                # Try to find headers in first row
                first_row = table.find('tr')
                if first_row:
                    potential_headers = first_row.find_all('th')
                    if potential_headers:
                        headers = [th.get_text(strip=True) for th in potential_headers]
            
            # Extract data rows
            tbody = table.find('tbody') or table
            for tr in tbody.find_all('tr'):
                # Skip header row if already processed
                if tr.find('th') and headers:
                    continue
                
                row = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                if row:
                    rows.append(row)
            
            # If no headers found, use first row
            if not headers and rows:
                headers = [f'Column_{i+1}' for i in range(len(rows[0]))]
            
            # Convert to structured format
            data = []
            for row in rows:
                if len(row) == len(headers):
                    data.append(dict(zip(headers, row)))
                else:
                    # Handle mismatched columns
                    row_dict = {}
                    for i, value in enumerate(row):
                        if i < len(headers):
                            row_dict[headers[i]] = value
                        else:
                            row_dict[f'Column_{i+1}'] = value
                    data.append(row_dict)
            
            return {
                'id': f'table_{index+1}',
                'data': data,
                'headers': headers,
                'rows': len(data),
                'columns': len(headers),
                'attributes': dict(table.attrs) if table.attrs else {}
            }
            
        except Exception as e:
            return None
    
    def _parse_excel_tables(self, file_path: str, options: Dict) -> Dict:
        """Parse tables from Excel files"""
        result = {
            'tables': [],
            'metadata': {'source': 'excel'},
            'errors': []
        }
        
        if not pd:
            result['errors'].append("pandas not installed")
            return result
        
        try:
            # Read all sheets
            excel_file = pd.ExcelFile(file_path)
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(
                    file_path,
                    sheet_name=sheet_name,
                    header=options.get('header_row', 0),
                    skiprows=options.get('skip_rows', 0)
                )
                
                # Clean column names
                df.columns = [str(col).strip() for col in df.columns]
                
                # Remove empty rows
                df = df.dropna(how='all')
                
                table_data = {
                    'id': f'sheet_{sheet_name}',
                    'sheet_name': sheet_name,
                    'data': df.to_dict('records'),
                    'headers': list(df.columns),
                    'rows': len(df),
                    'columns': len(df.columns)
                }
                
                result['tables'].append(table_data)
            
            result['metadata']['sheet_count'] = len(excel_file.sheet_names)
            
        except Exception as e:
            result['errors'].append(f"Excel parsing error: {str(e)}")
        
        return result
    
    def _parse_csv_table(self, source: str, options: Dict) -> Dict:
        """Parse CSV data"""
        result = {
            'tables': [],
            'metadata': {'source': 'csv'},
            'errors': []
        }
        
        try:
            # Check if source is file path or CSV content
            if Path(source).exists():
                with open(source, 'r', encoding=options.get('encoding', 'utf-8')) as f:
                    csv_content = f.read()
            else:
                csv_content = source
            
            # Parse CSV
            reader = csv.DictReader(StringIO(csv_content))
            data = list(reader)
            
            if data:
                table_data = {
                    'id': 'table_1',
                    'data': data,
                    'headers': reader.fieldnames,
                    'rows': len(data),
                    'columns': len(reader.fieldnames)
                }
                result['tables'].append(table_data)
            
        except Exception as e:
            result['errors'].append(f"CSV parsing error: {str(e)}")
        
        return result
    
    def _parse_text_tables(self, text: str, options: Dict) -> Dict:
        """Parse tables from plain text"""
        result = {
            'tables': [],
            'metadata': {'source': 'text'},
            'errors': []
        }
        
        try:
            # Check if text is file path or content
            if len(text) < 500 and Path(text).exists():
                with open(text, 'r', encoding=options.get('encoding', 'utf-8')) as f:
                    text = f.read()
            
            # Detect tables in text
            tables = self._detect_text_tables(text, options)
            
            for i, table_text in enumerate(tables):
                table_data = self._parse_text_table(table_text, options)
                if table_data:
                    table_data['id'] = f'table_{i+1}'
                    result['tables'].append(table_data)
            
        except Exception as e:
            result['errors'].append(f"Text parsing error: {str(e)}")
        
        return result
    
    def _detect_text_tables(self, text: str, options: Dict) -> List[str]:
        """Detect table-like structures in text"""
        tables = []
        lines = text.split('\n')
        
        # Look for patterns that indicate tables
        # Pattern 1: Lines with consistent delimiters (|, \t, multiple spaces)
        current_table = []
        delimiter_counts = []
        
        for line in lines:
            # Count delimiters
            pipe_count = line.count('|')
            tab_count = line.count('\t')
            multi_space_count = len(re.findall(r'  +', line))
            
            if pipe_count > 1 or tab_count > 1 or multi_space_count > 2:
                current_table.append(line)
                delimiter_counts.append((pipe_count, tab_count, multi_space_count))
            elif current_table:
                # Check if we have a valid table
                if len(current_table) > 1:
                    tables.append('\n'.join(current_table))
                current_table = []
                delimiter_counts = []
        
        # Add last table if exists
        if len(current_table) > 1:
            tables.append('\n'.join(current_table))
        
        return tables
    
    def _parse_text_table(self, table_text: str, options: Dict) -> Optional[Dict]:
        """Parse a text table"""
        lines = table_text.strip().split('\n')
        if not lines:
            return None
        
        # Detect delimiter
        delimiter = self._detect_delimiter(lines[0])
        
        # Parse table
        data = []
        headers = None
        
        for i, line in enumerate(lines):
            # Skip separator lines (e.g., |---|---|)
            if re.match(r'^[\|\-\+\s]+$', line):
                continue
            
            # Split by delimiter
            if delimiter == '|':
                cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            elif delimiter == '\t':
                cells = [cell.strip() for cell in line.split('\t')]
            else:
                # Multiple spaces
                cells = [cell.strip() for cell in re.split(r'  +', line)]
            
            if not headers:
                headers = cells
            else:
                # Create row dict
                row = {}
                for j, value in enumerate(cells):
                    if j < len(headers):
                        row[headers[j]] = value
                    else:
                        row[f'Column_{j+1}'] = value
                data.append(row)
        
        if not data:
            return None
        
        return {
            'data': data,
            'headers': headers,
            'rows': len(data),
            'columns': len(headers) if headers else 0,
            'delimiter': delimiter
        }
    
    def _detect_delimiter(self, line: str) -> str:
        """Detect the delimiter used in a line"""
        if '|' in line:
            return '|'
        elif '\t' in line:
            return '\t'
        elif re.search(r'  +', line):
            return '  '
        else:
            return ','
    
    def _calculate_statistics(self, tables: List[Dict]) -> Dict:
        """Calculate statistics for parsed tables"""
        stats = {
            'total_tables': len(tables),
            'total_rows': sum(t.get('rows', 0) for t in tables),
            'total_columns': sum(t.get('columns', 0) for t in tables),
            'average_rows': 0,
            'average_columns': 0,
            'data_types': {}
        }
        
        if tables:
            stats['average_rows'] = stats['total_rows'] / len(tables)
            stats['average_columns'] = stats['total_columns'] / len(tables)
            
            # Analyze data types
            for table in tables:
                if 'data' in table and table['data']:
                    for row in table['data'][:10]:  # Sample first 10 rows
                        for key, value in row.items():
                            data_type = self._detect_data_type(str(value))
                            if data_type not in stats['data_types']:
                                stats['data_types'][data_type] = 0
                            stats['data_types'][data_type] += 1
        
        return stats
    
    def _detect_data_type(self, value: str) -> str:
        """Detect the data type of a value"""
        value = value.strip()
        
        if not value:
            return 'empty'
        
        # Check for numeric
        try:
            float(value.replace(',', ''))
            return 'numeric'
        except:
            pass
        
        # Check for date patterns
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{2}/\d{2}/\d{4}',
            r'\d{2}-\d{2}-\d{4}'
        ]
        for pattern in date_patterns:
            if re.match(pattern, value):
                return 'date'
        
        # Check for boolean
        if value.lower() in ['true', 'false', 'yes', 'no']:
            return 'boolean'
        
        # Check for currency
        if re.match(r'[\$€£¥]\s*[\d,]+\.?\d*', value):
            return 'currency'
        
        # Check for percentage
        if re.match(r'[\d,]+\.?\d*\s*%', value):
            return 'percentage'
        
        return 'text'
    
    def export_tables(self, tables: List[Dict], format: str, output_path: str) -> bool:
        """Export tables to various formats"""
        try:
            if format == 'csv':
                return self._export_to_csv(tables, output_path)
            elif format == 'json':
                return self._export_to_json(tables, output_path)
            elif format == 'excel' and pd:
                return self._export_to_excel(tables, output_path)
            elif format == 'markdown':
                return self._export_to_markdown(tables, output_path)
            else:
                return False
        except Exception as e:
            return False
    
    def _export_to_csv(self, tables: List[Dict], output_path: str) -> bool:
        """Export tables to CSV files"""
        try:
            for i, table in enumerate(tables):
                file_path = output_path.replace('.csv', f'_{i+1}.csv') if len(tables) > 1 else output_path
                
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    if table.get('data'):
                        writer = csv.DictWriter(f, fieldnames=table['headers'])
                        writer.writeheader()
                        writer.writerows(table['data'])
            return True
        except:
            return False
    
    def _export_to_json(self, tables: List[Dict], output_path: str) -> bool:
        """Export tables to JSON"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(tables, f, indent=2, ensure_ascii=False)
            return True
        except:
            return False
    
    def _export_to_excel(self, tables: List[Dict], output_path: str) -> bool:
        """Export tables to Excel"""
        if not pd:
            return False
        
        try:
            with pd.ExcelWriter(output_path) as writer:
                for i, table in enumerate(tables):
                    if table.get('data'):
                        df = pd.DataFrame(table['data'])
                        sheet_name = table.get('sheet_name', f'Table_{i+1}')
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
            return True
        except:
            return False
    
    def _export_to_markdown(self, tables: List[Dict], output_path: str) -> bool:
        """Export tables to Markdown format"""
        try:
            markdown_content = []
            
            for i, table in enumerate(tables):
                if table.get('data') and table.get('headers'):
                    # Table title
                    markdown_content.append(f"## Table {i+1}")
                    markdown_content.append("")
                    
                    # Headers
                    headers = table['headers']
                    markdown_content.append('| ' + ' | '.join(headers) + ' |')
                    markdown_content.append('| ' + ' | '.join(['---'] * len(headers)) + ' |')
                    
                    # Data rows
                    for row in table['data']:
                        row_values = [str(row.get(h, '')) for h in headers]
                        markdown_content.append('| ' + ' | '.join(row_values) + ' |')
                    
                    markdown_content.append("")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(markdown_content))
            
            return True
        except:
            return False
    
    def validate_table_structure(self, table: Dict) -> Dict:
        """Validate and clean table structure"""
        validation = {
            'is_valid': True,
            'issues': [],
            'cleaned_table': None
        }
        
        if not table.get('data'):
            validation['is_valid'] = False
            validation['issues'].append('No data found')
            return validation
        
        # Check for consistent column count
        headers = table.get('headers', [])
        row_lengths = [len(row) for row in table['data']]
        
        if len(set(row_lengths)) > 1:
            validation['issues'].append('Inconsistent column count across rows')
        
        # Check for empty headers
        if not headers or any(not h for h in headers):
            validation['issues'].append('Missing or empty headers')
        
        # Check for duplicate headers
        if len(headers) != len(set(headers)):
            validation['issues'].append('Duplicate headers found')
        
        # Clean and return validated table
        cleaned_table = table.copy()
        
        # Ensure unique headers
        if headers:
            seen = {}
            unique_headers = []
            for h in headers:
                if h in seen:
                    seen[h] += 1
                    unique_headers.append(f"{h}_{seen[h]}")
                else:
                    seen[h] = 1
                    unique_headers.append(h)
            cleaned_table['headers'] = unique_headers
        
        validation['cleaned_table'] = cleaned_table
        
        return validation


if __name__ == "__main__":
    # Example usage
    import sys
    
    agent = TableParserAgent()
    print("Available parsers:", agent.available_parsers)
    
    if len(sys.argv) > 1:
        source = sys.argv[1]
        
        # Parse tables
        result = agent.parse_tables(source, source_type='auto')
        
        print(f"\nParsing: {source}")
        print(f"Tables found: {len(result['tables'])}")
        
        for table in result['tables']:
            print(f"\nTable ID: {table.get('id', 'unknown')}")
            print(f"  Rows: {table.get('rows', 0)}")
            print(f"  Columns: {table.get('columns', 0)}")
            print(f"  Headers: {table.get('headers', [])}")
            
            if table.get('data'):
                print(f"  Sample data (first row):")
                print(f"    {table['data'][0] if table['data'] else 'No data'}")
        
        if result.get('statistics'):
            print(f"\nStatistics: {result['statistics']}")
        
        if result.get('errors'):
            print(f"\nErrors: {result['errors']}")