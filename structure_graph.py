import tree_sitter
import tree_sitter_python
import tree_sitter_javascript
import tree_sitter_typescript
import hashlib
import uuid
from typing import Dict, Any, List, Optional
from storage import Storage
import os

class StructureGraph:
    def __init__(self, storage: Storage):
        self.storage = storage
        self.parsers = {}
        
        self.parsers['.py'] = tree_sitter.Parser(tree_sitter.Language(tree_sitter_python.language()))
        self.parsers['.js'] = tree_sitter.Parser(tree_sitter.Language(tree_sitter_javascript.language()))
        self.parsers['.jsx'] = tree_sitter.Parser(tree_sitter.Language(tree_sitter_javascript.language()))
        self.parsers['.ts'] = tree_sitter.Parser(tree_sitter.Language(tree_sitter_typescript.language_typescript()))
        self.parsers['.tsx'] = tree_sitter.Parser(tree_sitter.Language(tree_sitter_typescript.language_tsx()))
        
    def index(self, path: str, languages: Optional[List[str]] = None) -> Dict[str, Any]:
        """Parses a given file path and saves the extracted symbols to the symbols table."""
        abs_path = os.path.abspath(path)
        ext = os.path.splitext(abs_path)[1].lower()
        
        if ext not in self.parsers:
            return {"error": f"Unsupported file extension: {ext}"}
            
        if not os.path.exists(abs_path):
            return {"error": f"File not found: {abs_path}"}
            
        with open(abs_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        with self.storage.get_connection() as conn:
            cursor = conn.execute("SELECT content_hash FROM symbols WHERE file_path = ? LIMIT 1", (abs_path,))
            row = cursor.fetchone()
            if row and row['content_hash'] == content_hash:
                return {"status": "unchanged", "file_path": abs_path}
                
            conn.execute('''
                DELETE FROM calls 
                WHERE caller_id IN (SELECT id FROM symbols WHERE file_path = ?) 
                   OR callee_id IN (SELECT id FROM symbols WHERE file_path = ?)
            ''', (abs_path, abs_path))
            
            conn.execute("DELETE FROM symbols WHERE file_path = ?", (abs_path,))
            conn.commit()

        parser = self.parsers[ext]
        tree = parser.parse(bytes(content, 'utf8'))
        
        if ext == '.py':
            symbols, calls = self._extract_python_symbols_and_calls(tree.root_node, abs_path, content_hash)
        else:
            symbols, calls = self._extract_js_symbols_and_calls(tree.root_node, abs_path, content_hash)
        
        with self.storage.get_connection() as conn:
            for sym in symbols:
                conn.execute(
                    "INSERT INTO symbols (id, file_path, symbol_type, name, line_start, line_end, content_hash) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (sym['id'], sym['file_path'], sym['symbol_type'], sym['name'], sym['line_start'], sym['line_end'], sym['content_hash'])
                )
            
            for call in calls:
                conn.execute(
                    "INSERT OR IGNORE INTO calls (caller_id, callee_id) VALUES (?, ?)",
                    (call['caller_id'], call['callee_id'])
                )
                
            conn.commit()
            
        return {"status": "indexed", "file_path": abs_path, "symbols_count": len(symbols), "calls_count": len(calls)}

    def _extract_python_symbols_and_calls(self, root_node, file_path: str, content_hash: str):
        symbols = []
        raw_calls = []
        
        def traverse(node, parent_type=None, current_class=None, current_caller=None):
            my_class = current_class
            my_caller = current_caller
            if node.type == 'class_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    sym_name = name_node.text.decode('utf8')
                    symbols.append({
                        'id': str(uuid.uuid4()),
                        'file_path': file_path,
                        'symbol_type': 'class',
                        'name': sym_name,
                        'line_start': node.start_point[0] + 1,
                        'line_end': node.end_point[0] + 1,
                        'content_hash': content_hash,
                        '_internal_key': sym_name
                    })
                    my_class = sym_name
                    my_caller = sym_name
                parent_type = 'class'
            elif node.type == 'function_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    sym_name = name_node.text.decode('utf8')
                    sym_type = 'method' if parent_type == 'class' else 'function'
                    
                    internal_key = (my_class, sym_name) if sym_type == 'method' else sym_name
                    
                    symbols.append({
                        'id': str(uuid.uuid4()),
                        'file_path': file_path,
                        'symbol_type': sym_type,
                        'name': sym_name,
                        'line_start': node.start_point[0] + 1,
                        'line_end': node.end_point[0] + 1,
                        'content_hash': content_hash,
                        '_internal_key': internal_key
                    })
                    my_caller = internal_key
            elif node.type == 'call':
                func_node = node.child_by_field_name('function')
                if func_node and current_caller:
                    if func_node.type == 'identifier':
                        callee_name = func_node.text.decode('utf8')
                        raw_calls.append((current_caller, callee_name, False, current_class))
                    elif func_node.type == 'attribute':
                        attr_node = func_node.child_by_field_name('attribute')
                        if attr_node:
                            callee_name = attr_node.text.decode('utf8')
                            raw_calls.append((current_caller, callee_name, True, current_class))
            
            for child in node.children:
                traverse(child, parent_type, my_class, my_caller)
                
        traverse(root_node)
        
        symbol_map = {sym['_internal_key']: sym['id'] for sym in symbols}
        global_name_map = {}
        for sym in symbols:
            if sym['symbol_type'] == 'function':
                global_name_map[sym['name']] = sym['id']
        for sym in symbols:
            if sym['name'] not in global_name_map:
                global_name_map[sym['name']] = sym['id']

        resolved_calls = []
        for caller_key, callee_name, is_attr, caller_class in raw_calls:
            caller_id = symbol_map.get(caller_key)
            callee_id = None
            
            if is_attr and caller_class:
                callee_key = (caller_class, callee_name)
                if callee_key in symbol_map:
                    callee_id = symbol_map[callee_key]
            
            if not callee_id:
                callee_id = global_name_map.get(callee_name)
                    
            if caller_id and callee_id:
                resolved_calls.append({
                    'caller_id': caller_id,
                    'callee_id': callee_id
                })
                
        for sym in symbols:
            del sym['_internal_key']
            
        return symbols, resolved_calls

    def _extract_js_symbols_and_calls(self, root_node, file_path: str, content_hash: str):
        symbols = []
        raw_calls = []
        
        def traverse(node, parent_type=None, current_class=None, current_caller=None):
            my_class = current_class
            my_caller = current_caller
            if node.type == 'class_declaration':
                name_node = node.child_by_field_name('name')
                if name_node:
                    sym_name = name_node.text.decode('utf8')
                    symbols.append({
                        'id': str(uuid.uuid4()),
                        'file_path': file_path,
                        'symbol_type': 'class',
                        'name': sym_name,
                        'line_start': node.start_point[0] + 1,
                        'line_end': node.end_point[0] + 1,
                        'content_hash': content_hash,
                        '_internal_key': sym_name
                    })
                    my_class = sym_name
                    my_caller = sym_name
                parent_type = 'class'
            elif node.type == 'function_declaration' or node.type == 'method_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    sym_name = name_node.text.decode('utf8')
                    sym_type = 'method' if node.type == 'method_definition' else 'function'
                    
                    internal_key = (my_class, sym_name) if sym_type == 'method' else sym_name
                    
                    symbols.append({
                        'id': str(uuid.uuid4()),
                        'file_path': file_path,
                        'symbol_type': sym_type,
                        'name': sym_name,
                        'line_start': node.start_point[0] + 1,
                        'line_end': node.end_point[0] + 1,
                        'content_hash': content_hash,
                        '_internal_key': internal_key
                    })
                    my_caller = internal_key
            elif node.type == 'call_expression':
                func_node = node.child_by_field_name('function')
                if func_node and current_caller:
                    if func_node.type == 'identifier':
                        callee_name = func_node.text.decode('utf8')
                        raw_calls.append((current_caller, callee_name, False, current_class))
                    elif func_node.type == 'member_expression':
                        prop_node = func_node.child_by_field_name('property')
                        if prop_node:
                            callee_name = prop_node.text.decode('utf8')
                            raw_calls.append((current_caller, callee_name, True, current_class))
            
            for child in node.children:
                traverse(child, parent_type, my_class, my_caller)
                
        traverse(root_node)
        
        symbol_map = {sym['_internal_key']: sym['id'] for sym in symbols}
        global_name_map = {}
        for sym in symbols:
            if sym['symbol_type'] == 'function':
                global_name_map[sym['name']] = sym['id']
        for sym in symbols:
            if sym['name'] not in global_name_map:
                global_name_map[sym['name']] = sym['id']

        resolved_calls = []
        for caller_key, callee_name, is_attr, caller_class in raw_calls:
            caller_id = symbol_map.get(caller_key)
            callee_id = None
            
            if is_attr and caller_class:
                callee_key = (caller_class, callee_name)
                if callee_key in symbol_map:
                    callee_id = symbol_map[callee_key]
            
            if not callee_id:
                callee_id = global_name_map.get(callee_name)
                    
            if caller_id and callee_id:
                resolved_calls.append({
                    'caller_id': caller_id,
                    'callee_id': callee_id
                })
                
        for sym in symbols:
            del sym['_internal_key']
            
        return symbols, resolved_calls

    def get_symbol(self, name: str) -> List[Dict[str, Any]]:
        """Retrieves a symbol's info, file, and line numbers from the database."""
        with self.storage.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM symbols WHERE name = ?", (name,))
            return [dict(row) for row in cursor.fetchall()]

    def trace_calls(self, symbol_name: str, direction: str) -> List[Dict[str, Any]]:
        """Returns the inbound or outbound call chain for a given symbol. direction: 'inbound' or 'outbound'"""
        if direction not in ['inbound', 'outbound']:
            return [{"error": "Direction must be 'inbound' or 'outbound'"}]
            
        with self.storage.get_connection() as conn:
            cursor = conn.execute("SELECT id, name FROM symbols WHERE name = ?", (symbol_name,))
            symbols = cursor.fetchall()
            if not symbols:
                return []
                
            results = []
            for sym in symbols:
                sym_id = sym['id']
                if direction == 'outbound':
                    query = '''
                        SELECT s.name, s.file_path, s.line_start
                        FROM calls c
                        JOIN symbols s ON c.callee_id = s.id
                        WHERE c.caller_id = ?
                    '''
                    c = conn.execute(query, (sym_id,))
                    callees = [dict(row) for row in c.fetchall()]
                    results.append({"symbol": sym['name'], "calls": callees})
                else:
                    query = '''
                        SELECT s.name, s.file_path, s.line_start
                        FROM calls c
                        JOIN symbols s ON c.caller_id = s.id
                        WHERE c.callee_id = ?
                    '''
                    c = conn.execute(query, (sym_id,))
                    callers = [dict(row) for row in c.fetchall()]
                    results.append({"symbol": sym['name'], "called_by": callers})
                    
            return results

    def get_architecture(self) -> Dict[str, Any]:
        """Returns a basic high-level overview of the parsed codebase, including files, symbol counts, and uncalled symbols."""
        with self.storage.get_connection() as conn:
            c = conn.execute("SELECT DISTINCT file_path FROM symbols")
            files = [row['file_path'] for row in c.fetchall()]
            
            c = conn.execute("SELECT symbol_type, COUNT(*) as count FROM symbols GROUP BY symbol_type")
            counts = {row['symbol_type']: row['count'] for row in c.fetchall()}
            
            query = '''
                SELECT name, symbol_type, file_path 
                FROM symbols 
                WHERE id NOT IN (SELECT DISTINCT callee_id FROM calls)
            '''
            c = conn.execute(query)
            uncalled_within_file = [dict(row) for row in c.fetchall()]
            
            return {
                "files": files,
                "symbol_counts": counts,
                "uncalled_within_file": uncalled_within_file,
                "note": "Methods called only via an external instance (e.g. obj.method()) will appear here since cross-file/instance calls aren't tracked yet."
            }
