#!/usr/bin/env python3
import argparse
import csv
import sys
import re
import random
import json
import statistics
from collections import Counter
from datetime import datetime

def read_csv(filepath):
    if filepath == '-':
        reader = csv.DictReader(sys.stdin)
    else:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    if filepath == '-':
        rows = list(reader)
    return rows

def write_csv(rows, filepath, output_format='csv'):
    if not rows:
        return
    fields = rows[0].keys()
    
    if output_format == 'csv':
        if filepath == '-':
            writer = csv.DictWriter(sys.stdout, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        else:
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
    elif output_format == 'tsv':
        if filepath == '-':
            writer = csv.DictWriter(sys.stdout, fieldnames=fields, delimiter='\t')
            writer.writeheader()
            writer.writerows(rows)
        else:
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fields, delimiter='\t')
                writer.writeheader()
                writer.writerows(rows)
    elif output_format == 'json':
        if filepath == '-':
            print(json.dumps(rows, indent=2, ensure_ascii=False))
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(rows, f, indent=2, ensure_ascii=False)
    elif output_format == 'markdown':
        md = []
        md.append('| ' + ' | '.join(fields) + ' |')
        md.append('|' + '|'.join(['---'] * len(fields)) + '|')
        for row in rows:
            md.append('| ' + ' | '.join(str(row.get(f, '')) for f in fields) + ' |')
        output = '\n'.join(md)
        if filepath == '-':
            print(output)
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(output)
    elif output_format == 'sql':
        table_name = filepath.replace('.sql', '').replace('-', '_').replace('.', '_') if filepath != '-' else 'mytable'
        sql_lines = []
        for row in rows:
            cols = ', '.join(fields)
            values = []
            for f in fields:
                v = str(row.get(f, ''))
                v = v.replace("'", "''")
                values.append("'%s'" % v)
            vals = ', '.join(values)
            sql_lines.append("INSERT INTO %s (%s) VALUES (%s);" % (table_name, cols, vals))
        output = '\n'.join(sql_lines)
        if filepath == '-':
            print(output)
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(output)

def infer_type(value):
    if not value:
        return 'null'
    try:
        int(value)
        return 'int'
    except:
        pass
    try:
        float(value)
        return 'float'
    except:
        pass
    try:
        datetime.strptime(value, '%Y-%m-%d')
        return 'date'
    except:
        pass
    try:
        datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        return 'datetime'
    except:
        pass
    return 'str'

def cmd_head(args):
    rows = read_csv(args.file)
    n = args.n
    write_csv(rows[:n], args.output, args.format)

def cmd_tail(args):
    rows = read_csv(args.file)
    n = args.n
    write_csv(rows[-n:], args.output, args.format)

def cmd_columns(args):
    rows = read_csv(args.file)
    if not rows:
        return
    fields = rows[0].keys()
    type_counts = {f: [] for f in fields}
    for row in rows[:100]:
        for f in fields:
            type_counts[f].append(infer_type(row[f]))
    results = []
    for f in fields:
        types = type_counts[f]
        if types:
            most_common = Counter(types).most_common(1)[0][0]
        else:
            most_common = 'unknown'
        results.append({'column': f, 'type': most_common})
    
    if args.format == 'json':
        print(json.dumps(results, indent=2))
    else:
        print(f"{'Column':<20} {'Type':<10}")
        print('-' * 30)
        for r in results:
            print(f"{r['column']:<20} {r['type']:<10}")

def cmd_count(args):
    rows = read_csv(args.file)
    print(len(rows))

def cmd_select(args):
    rows = read_csv(args.file)
    cols = args.columns.split(',')
    cols = [c.strip() for c in cols]
    new_rows = []
    for row in rows:
        new_row = {c: row.get(c, '') for c in cols}
        new_rows.append(new_row)
    write_csv(new_rows, args.output, args.format)

def cmd_rename(args):
    rows = read_csv(args.file)
    mappings = args.mappings.split(',')
    rename_dict = {}
    for m in mappings:
        old, new = m.split('=')
        rename_dict[old.strip()] = new.strip()
    new_rows = []
    for row in rows:
        new_row = {}
        for k, v in row.items():
            new_row[rename_dict.get(k, k)] = v
        new_rows.append(new_row)
    write_csv(new_rows, args.output, args.format)

def cmd_reorder(args):
    rows = read_csv(args.file)
    cols = args.columns.split(',')
    cols = [c.strip() for c in cols]
    new_rows = []
    for row in rows:
        new_row = {c: row.get(c, '') for c in cols}
        new_rows.append(new_row)
    write_csv(new_rows, args.output, args.format)

def parse_condition(cond_str):
    operators = [('>=', 'ge'), ('<=', 'le'), ('!=', 'ne'), ('==', 'eq'), ('=', 'eq'), 
                 ('>', 'gt'), ('<', 'lt'), ('contains', 'contains'), ('regex', 'regex')]
    for op, op_name in operators:
        if op in cond_str:
            parts = cond_str.split(op, 1)
            col = parts[0].strip()
            value = parts[1].strip()
            value = value.strip('\'"')
            return (col, op_name, value)
    return None

def eval_condition(row, cond):
    col, op, value = cond
    row_val = row.get(col, '')
    
    if op in ('gt', 'lt', 'ge', 'le', 'eq', 'ne'):
        try:
            row_val_num = float(row_val)
            value_num = float(value)
            if op == 'gt':
                return row_val_num > value_num
            elif op == 'lt':
                return row_val_num < value_num
            elif op == 'ge':
                return row_val_num >= value_num
            elif op == 'le':
                return row_val_num <= value_num
            elif op == 'eq':
                return row_val_num == value_num
            elif op == 'ne':
                return row_val_num != value_num
        except:
            if op == 'eq':
                return str(row_val) == str(value)
            elif op == 'ne':
                return str(row_val) != str(value)
            return False
    elif op == 'contains':
        return value in str(row_val)
    elif op == 'regex':
        try:
            return bool(re.search(value, str(row_val)))
        except:
            return False
    return False

def cmd_where(args):
    rows = read_csv(args.file)
    conditions = args.conditions.split('&&')
    conditions = [c.strip() for c in conditions]
    parsed_conds = [parse_condition(c) for c in conditions]
    
    filtered = []
    for row in rows:
        match = True
        for cond in parsed_conds:
            if cond and not eval_condition(row, cond):
                match = False
                break
        if match:
            filtered.append(row)
    write_csv(filtered, args.output, args.format)

def cmd_sort(args):
    rows = read_csv(args.file)
    sort_specs = args.columns.split(',')
    key_funcs = []
    reverse_flags = []
    for spec in sort_specs:
        spec = spec.strip()
        if spec.startswith('-'):
            col = spec[1:]
            reverse_flags.append(True)
        elif spec.startswith('desc:'):
            col = spec[5:]
            reverse_flags.append(True)
        else:
            col = spec
            reverse_flags.append(False)
        key_funcs.append(col)
    
    def sort_key(row):
        keys = []
        for i, col in enumerate(key_funcs):
            val = row.get(col, '')
            try:
                keys.append(float(val))
            except:
                keys.append(val)
        return keys
    
    rows.sort(key=sort_key, reverse=any(reverse_flags))
    write_csv(rows, args.output, args.format)

def cmd_unique(args):
    rows = read_csv(args.file)
    cols = args.columns.split(',') if args.columns else None
    seen = set()
    unique_rows = []
    
    for row in rows:
        if cols:
            key = tuple(row.get(c, '') for c in cols)
        else:
            key = tuple(row.items())
        if key not in seen:
            seen.add(key)
            unique_rows.append(row)
    write_csv(unique_rows, args.output, args.format)

def cmd_sample(args):
    rows = read_csv(args.file)
    n = args.n
    sampled = random.sample(rows, min(n, len(rows)))
    write_csv(sampled, args.output, args.format)

def cmd_mutate(args):
    rows = read_csv(args.file)
    exprs = args.expressions.split(',')
    
    for row in rows:
        for expr in exprs:
            parts = expr.split('=', 1)
            if len(parts) != 2:
                continue
            new_col = parts[0].strip()
            expression = parts[1].strip()
            
            local_vars = row.copy()
            for k, v in local_vars.items():
                try:
                    local_vars[k] = float(v)
                except:
                    pass
            
            try:
                result = eval(expression, {}, local_vars)
                row[new_col] = str(result)
            except:
                row[new_col] = ''
    
    write_csv(rows, args.output, args.format)

def cmd_fill(args):
    rows = read_csv(args.file)
    col = args.column
    method = args.method
    value = args.value
    
    if method == 'ffill':
        prev_val = ''
        for row in rows:
            if row.get(col, '').strip():
                prev_val = row[col]
            else:
                row[col] = prev_val
    elif method == 'bfill':
        next_val = ''
        for row in reversed(rows):
            if row.get(col, '').strip():
                next_val = row[col]
            else:
                row[col] = next_val
    elif method == 'value':
        for row in rows:
            if not row.get(col, '').strip():
                row[col] = value
    elif method == 'mean':
        values = []
        for row in rows:
            try:
                values.append(float(row.get(col, '')))
            except:
                pass
        if values:
            mean_val = sum(values) / len(values)
            for row in rows:
                if not row.get(col, '').strip():
                    row[col] = str(mean_val)
    
    write_csv(rows, args.output, args.format)

def cmd_split_col(args):
    rows = read_csv(args.file)
    col = args.column
    sep = args.separator
    new_cols = args.new_columns.split(',') if args.new_columns else None
    
    for row in rows:
        val = row.get(col, '')
        parts = val.split(sep)
        if new_cols:
            for i, nc in enumerate(new_cols):
                row[nc.strip()] = parts[i] if i < len(parts) else ''
        else:
            for i, part in enumerate(parts):
                row[f"{col}_{i+1}"] = part
    
    write_csv(rows, args.output, args.format)

def cmd_merge_cols(args):
    rows = read_csv(args.file)
    cols = args.columns.split(',')
    sep = args.separator
    new_col = args.new_column
    
    for row in rows:
        vals = [row.get(c.strip(), '') for c in cols]
        row[new_col] = sep.join(vals)
    
    write_csv(rows, args.output, args.format)

def cmd_groupby(args):
    rows = read_csv(args.file)
    group_cols = args.group.split(',')
    agg_specs = args.agg.split(',')
    
    groups = {}
    for row in rows:
        key = tuple(row.get(c.strip(), '') for c in group_cols)
        if key not in groups:
            groups[key] = []
        groups[key].append(row)
    
    agg_results = []
    for key, group_rows in groups.items():
        result = dict(zip(group_cols, key))
        for agg in agg_specs:
            parts = agg.split(':')
            if len(parts) != 2:
                continue
            func_name = parts[0].strip()
            col = parts[1].strip()
            
            values = []
            for r in group_rows:
                try:
                    values.append(float(r.get(col, '')))
                except:
                    pass
            
            if func_name == 'sum':
                result[f"{col}_sum"] = sum(values)
            elif func_name == 'avg':
                result[f"{col}_avg"] = sum(values) / len(values) if values else 0
            elif func_name == 'count':
                result[f"{col}_count"] = len([r for r in group_rows if r.get(col, '').strip()])
            elif func_name == 'min':
                result[f"{col}_min"] = min(values) if values else ''
            elif func_name == 'max':
                result[f"{col}_max"] = max(values) if values else ''
            elif func_name == 'std':
                result[f"{col}_std"] = statistics.stdev(values) if len(values) > 1 else 0
        agg_results.append(result)
    
    write_csv(agg_results, args.output, args.format)

def cmd_pivot(args):
    rows = read_csv(args.file)
    row_col = args.row
    col_col = args.col
    val_col = args.value
    agg_func = args.agg or 'sum'
    
    row_values = sorted(set(r.get(row_col, '') for r in rows))
    col_values = sorted(set(r.get(col_col, '') for r in rows))
    
    headers = [row_col] + col_values
    pivot_rows = []
    
    for rv in row_values:
        row = {row_col: rv}
        for cv in col_values:
            filtered = [r for r in rows if r.get(row_col) == rv and r.get(col_col) == cv]
            values = []
            for r in filtered:
                try:
                    values.append(float(r.get(val_col, '')))
                except:
                    pass
            
            if agg_func == 'sum':
                row[cv] = sum(values)
            elif agg_func == 'avg':
                row[cv] = sum(values) / len(values) if values else 0
            elif agg_func == 'count':
                row[cv] = len(filtered)
            elif agg_func == 'min':
                row[cv] = min(values) if values else ''
            elif agg_func == 'max':
                row[cv] = max(values) if values else ''
        pivot_rows.append(row)
    
    write_csv(pivot_rows, args.output, args.format)

def cmd_describe(args):
    rows = read_csv(args.file)
    if not rows:
        return
    
    fields = rows[0].keys()
    results = []
    
    for field in fields:
        stats = {'column': field}
        values = [r.get(field, '') for r in rows]
        non_null_values = [v for v in values if v.strip()]
        
        type_counts = Counter([infer_type(v) for v in non_null_values])
        main_type = type_counts.most_common(1)[0][0] if type_counts else 'null'
        stats['type'] = main_type
        
        if main_type in ('int', 'float'):
            num_values = []
            for v in non_null_values:
                try:
                    num_values.append(float(v))
                except:
                    pass
            if num_values:
                stats['count'] = len(num_values)
                stats['mean'] = sum(num_values) / len(num_values)
                stats['std'] = statistics.stdev(num_values) if len(num_values) > 1 else 0
                stats['min'] = min(num_values)
                stats['max'] = max(num_values)
                sorted_vals = sorted(num_values)
                n = len(sorted_vals)
                if n % 2 == 0:
                    stats['median'] = (sorted_vals[n//2 - 1] + sorted_vals[n//2]) / 2
                else:
                    stats['median'] = sorted_vals[n//2]
        else:
            stats['count'] = len(non_null_values)
            stats['unique'] = len(set(non_null_values))
            if non_null_values:
                stats['top'] = Counter(non_null_values).most_common(1)[0][0]
                stats['freq'] = Counter(non_null_values).most_common(1)[0][1]
        
        results.append(stats)
    
    if args.format == 'json':
        print(json.dumps(results, indent=2))
    else:
        headers = ['column', 'type', 'count']
        if results:
            sample = results[0]
            if 'mean' in sample:
                headers.extend(['mean', 'median', 'std', 'min', 'max'])
            elif 'unique' in sample:
                headers.extend(['unique', 'top', 'freq'])
        
        print(' | '.join(f'{h:<15}' for h in headers))
        print('-' * (len(headers) * 17))
        for r in results:
            row_parts = []
            for h in headers:
                val = r.get(h, '')
                if isinstance(val, float):
                    val = f'{val:.2f}'
                row_parts.append(f'{val:<15}')
            print(' | '.join(row_parts))

def cmd_join(args):
    left_rows = read_csv(args.left)
    right_rows = read_csv(args.right)
    left_on = args.left_on
    right_on = args.right_on or left_on
    how = args.how
    
    right_index = {}
    for row in right_rows:
        key = row.get(right_on, '')
        if key not in right_index:
            right_index[key] = []
        right_index[key].append(row)
    
    result_rows = []
    
    for left_row in left_rows:
        left_key = left_row.get(left_on, '')
        matched_right = right_index.get(left_key, [])
        
        if matched_right:
            for right_row in matched_right:
                new_row = left_row.copy()
                for k, v in right_row.items():
                    if k != right_on:
                        new_row[k] = v
                result_rows.append(new_row)
        elif how in ('left', 'outer'):
            new_row = left_row.copy()
            for k in right_rows[0].keys():
                if k != right_on and k not in new_row:
                    new_row[k] = ''
            result_rows.append(new_row)
    
    if how in ('right', 'outer'):
        left_keys = set(r.get(left_on, '') for r in left_rows)
        for right_row in right_rows:
            right_key = right_row.get(right_on, '')
            if right_key not in left_keys:
                new_row = right_row.copy()
                for k in left_rows[0].keys():
                    if k != left_on and k not in new_row:
                        new_row[k] = ''
                result_rows.append(new_row)
    
    write_csv(result_rows, args.output, args.format)

def cmd_concat(args):
    files = args.files.split(',')
    all_rows = []
    fields = set()
    
    for f in files:
        rows = read_csv(f.strip())
        if rows:
            fields.update(rows[0].keys())
            all_rows.extend(rows)
    
    fields = sorted(fields)
    normalized_rows = []
    for row in all_rows:
        new_row = {}
        for f in fields:
            new_row[f] = row.get(f, '')
        normalized_rows.append(new_row)
    
    write_csv(normalized_rows, args.output, args.format)

def cmd_diff(args):
    left_rows = read_csv(args.left)
    right_rows = read_csv(args.right)
    
    left_key = args.key
    right_key = args.key
    
    left_index = {r.get(left_key, ''): r for r in left_rows}
    right_index = {r.get(right_key, ''): r for r in right_rows}
    
    added = []
    removed = []
    modified = []
    
    for key, row in right_index.items():
        if key not in left_index:
            added.append({'type': 'added', **row})
        else:
            if left_index[key] != row:
                modified.append({'type': 'modified', 'old': left_index[key], 'new': row})
    
    for key, row in left_index.items():
        if key not in right_index:
            removed.append({'type': 'removed', **row})
    
    if args.format == 'json':
        result = {'added': added, 'removed': removed, 'modified': modified}
        print(json.dumps(result, indent=2))
    else:
        print("Added:")
        print("-" * 50)
        if added:
            write_csv(added, '-', 'csv')
        else:
            print("None")
        
        print("\nRemoved:")
        print("-" * 50)
        if removed:
            write_csv(removed, '-', 'csv')
        else:
            print("None")
        
        print("\nModified:")
        print("-" * 50)
        for m in modified:
            print(f"Key: {m['old'].get(args.key, '')}")
            print(f"  Old: {m['old']}")
            print(f"  New: {m['new']}")

def cmd_split_file(args):
    rows = read_csv(args.file)
    split_col = args.column
    
    groups = {}
    for row in rows:
        key = row.get(split_col, 'unknown')
        if key not in groups:
            groups[key] = []
        groups[key].append(row)
    
    for key, group_rows in groups.items():
        safe_key = str(key).replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        filename = f"{safe_key}.csv"
        write_csv(group_rows, filename, 'csv')
        print(f"Wrote {len(group_rows)} rows to {filename}")

def main():
    parser = argparse.ArgumentParser(prog='csvrack', description='CSV data processing tool')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    p_head = subparsers.add_parser('head', help='Show first N rows')
    p_head.add_argument('file', nargs='?', default='-', help='Input CSV file')
    p_head.add_argument('-n', type=int, default=10, help='Number of rows')
    p_head.add_argument('-o', '--output', default='-', help='Output file')
    p_head.add_argument('-f', '--format', default='csv', choices=['csv', 'tsv', 'json', 'markdown', 'sql'], help='Output format')
    
    p_tail = subparsers.add_parser('tail', help='Show last N rows')
    p_tail.add_argument('file', nargs='?', default='-', help='Input CSV file')
    p_tail.add_argument('-n', type=int, default=10, help='Number of rows')
    p_tail.add_argument('-o', '--output', default='-', help='Output file')
    p_tail.add_argument('-f', '--format', default='csv', choices=['csv', 'tsv', 'json', 'markdown', 'sql'], help='Output format')
    
    p_columns = subparsers.add_parser('columns', help='List columns and infer types')
    p_columns.add_argument('file', nargs='?', default='-', help='Input CSV file')
    p_columns.add_argument('-f', '--format', default='text', choices=['text', 'json'], help='Output format')
    
    p_count = subparsers.add_parser('count', help='Count rows')
    p_count.add_argument('file', nargs='?', default='-', help='Input CSV file')
    
    p_select = subparsers.add_parser('select', help='Select specific columns')
    p_select.add_argument('file', nargs='?', default='-', help='Input CSV file')
    p_select.add_argument('columns', help='Comma-separated column names')
    p_select.add_argument('-o', '--output', default='-', help='Output file')
    p_select.add_argument('-f', '--format', default='csv', choices=['csv', 'tsv', 'json', 'markdown', 'sql'], help='Output format')
    
    p_rename = subparsers.add_parser('rename', help='Rename columns')
    p_rename.add_argument('file', nargs='?', default='-', help='Input CSV file')
    p_rename.add_argument('mappings', help='Old=New comma-separated mappings')
    p_rename.add_argument('-o', '--output', default='-', help='Output file')
    p_rename.add_argument('-f', '--format', default='csv', choices=['csv', 'tsv', 'json', 'markdown', 'sql'], help='Output format')
    
    p_reorder = subparsers.add_parser('reorder', help='Reorder columns')
    p_reorder.add_argument('file', nargs='?', default='-', help='Input CSV file')
    p_reorder.add_argument('columns', help='Comma-separated column order')
    p_reorder.add_argument('-o', '--output', default='-', help='Output file')
    p_reorder.add_argument('-f', '--format', default='csv', choices=['csv', 'tsv', 'json', 'markdown', 'sql'], help='Output format')
    
    p_where = subparsers.add_parser('where', help='Filter rows by condition')
    p_where.add_argument('file', nargs='?', default='-', help='Input CSV file')
    p_where.add_argument('conditions', help='Conditions (e.g., age>30&&name contains "John")')
    p_where.add_argument('-o', '--output', default='-', help='Output file')
    p_where.add_argument('-f', '--format', default='csv', choices=['csv', 'tsv', 'json', 'markdown', 'sql'], help='Output format')
    
    p_sort = subparsers.add_parser('sort', help='Sort rows')
    p_sort.add_argument('file', nargs='?', default='-', help='Input CSV file')
    p_sort.add_argument('columns', help='Comma-separated columns (use - for desc)')
    p_sort.add_argument('-o', '--output', default='-', help='Output file')
    p_sort.add_argument('-f', '--format', default='csv', choices=['csv', 'tsv', 'json', 'markdown', 'sql'], help='Output format')
    
    p_unique = subparsers.add_parser('unique', help='Get unique rows')
    p_unique.add_argument('file', nargs='?', default='-', help='Input CSV file')
    p_unique.add_argument('columns', nargs='?', help='Comma-separated columns for uniqueness')
    p_unique.add_argument('-o', '--output', default='-', help='Output file')
    p_unique.add_argument('-f', '--format', default='csv', choices=['csv', 'tsv', 'json', 'markdown', 'sql'], help='Output format')
    
    p_sample = subparsers.add_parser('sample', help='Random sample rows')
    p_sample.add_argument('file', nargs='?', default='-', help='Input CSV file')
    p_sample.add_argument('n', type=int, help='Number of rows')
    p_sample.add_argument('-o', '--output', default='-', help='Output file')
    p_sample.add_argument('-f', '--format', default='csv', choices=['csv', 'tsv', 'json', 'markdown', 'sql'], help='Output format')
    
    p_mutate = subparsers.add_parser('mutate', help='Add computed columns')
    p_mutate.add_argument('file', nargs='?', default='-', help='Input CSV file')
    p_mutate.add_argument('expressions', help='New column expressions (e.g., total=price*quantity)')
    p_mutate.add_argument('-o', '--output', default='-', help='Output file')
    p_mutate.add_argument('-f', '--format', default='csv', choices=['csv', 'tsv', 'json', 'markdown', 'sql'], help='Output format')
    
    fill_choices = ['ffill', 'bfill', 'value', 'mean']
    p_fill = subparsers.add_parser('fill', help='Fill missing values')
    p_fill.add_argument('file', nargs='?', default='-', help='Input CSV file')
    p_fill.add_argument('column', help='Column name')
    p_fill.add_argument('method', choices=fill_choices, help='Fill method')
    p_fill.add_argument('-v', '--value', default='', help='Value for value method')
    p_fill.add_argument('-o', '--output', default='-', help='Output file')
    p_fill.add_argument('-f', '--format', default='csv', choices=['csv', 'tsv', 'json', 'markdown', 'sql'], help='Output format')
    
    p_split = subparsers.add_parser('split', help='Split column')
    p_split.add_argument('file', nargs='?', default='-', help='Input CSV file')
    p_split.add_argument('column', help='Column to split')
    p_split.add_argument('-s', '--separator', default=',', help='Separator')
    p_split.add_argument('--new-columns', help='Comma-separated new column names')
    p_split.add_argument('-o', '--output', default='-', help='Output file')
    p_split.add_argument('-f', '--format', default='csv', choices=['csv', 'tsv', 'json', 'markdown', 'sql'], help='Output format')
    
    p_merge = subparsers.add_parser('merge', help='Merge columns')
    p_merge.add_argument('file', nargs='?', default='-', help='Input CSV file')
    p_merge.add_argument('columns', help='Comma-separated columns to merge')
    p_merge.add_argument('-s', '--separator', default=' ', help='Separator')
    p_merge.add_argument('-n', '--new-column', default='merged', help='New column name')
    p_merge.add_argument('-o', '--output', default='-', help='Output file')
    p_merge.add_argument('-f', '--format', default='csv', choices=['csv', 'tsv', 'json', 'markdown', 'sql'], help='Output format')
    
    p_groupby = subparsers.add_parser('groupby', help='Group by columns')
    p_groupby.add_argument('file', nargs='?', default='-', help='Input CSV file')
    p_groupby.add_argument('group', help='Comma-separated group columns')
    p_groupby.add_argument('agg', help='Aggregation specs (e.g., sum:price,avg:quantity)')
    p_groupby.add_argument('-o', '--output', default='-', help='Output file')
    p_groupby.add_argument('-f', '--format', default='csv', choices=['csv', 'tsv', 'json', 'markdown', 'sql'], help='Output format')
    
    p_pivot = subparsers.add_parser('pivot', help='Create pivot table')
    p_pivot.add_argument('file', nargs='?', default='-', help='Input CSV file')
    p_pivot.add_argument('row', help='Row column')
    p_pivot.add_argument('col', help='Column column')
    p_pivot.add_argument('value', help='Value column')
    p_pivot.add_argument('-a', '--agg', default='sum', choices=['sum', 'avg', 'count', 'min', 'max'], help='Aggregation function')
    p_pivot.add_argument('-o', '--output', default='-', help='Output file')
    p_pivot.add_argument('-f', '--format', default='csv', choices=['csv', 'tsv', 'json', 'markdown', 'sql'], help='Output format')
    
    p_describe = subparsers.add_parser('describe', help='Describe columns')
    p_describe.add_argument('file', nargs='?', default='-', help='Input CSV file')
    p_describe.add_argument('-f', '--format', default='text', choices=['text', 'json'], help='Output format')
    
    p_join = subparsers.add_parser('join', help='Join two CSV files')
    p_join.add_argument('left', help='Left CSV file')
    p_join.add_argument('right', help='Right CSV file')
    p_join.add_argument('--left-on', required=True, help='Left join column')
    p_join.add_argument('--right-on', help='Right join column (default same as left-on)')
    p_join.add_argument('--how', default='inner', choices=['inner', 'left', 'right', 'outer'], help='Join type')
    p_join.add_argument('-o', '--output', default='-', help='Output file')
    p_join.add_argument('-f', '--format', default='csv', choices=['csv', 'tsv', 'json', 'markdown', 'sql'], help='Output format')
    
    p_concat = subparsers.add_parser('concat', help='Concatenate CSV files')
    p_concat.add_argument('files', help='Comma-separated CSV files')
    p_concat.add_argument('-o', '--output', default='-', help='Output file')
    p_concat.add_argument('-f', '--format', default='csv', choices=['csv', 'tsv', 'json', 'markdown', 'sql'], help='Output format')
    
    p_diff = subparsers.add_parser('diff', help='Compare two CSV files')
    p_diff.add_argument('left', help='Left CSV file')
    p_diff.add_argument('right', help='Right CSV file')
    p_diff.add_argument('-k', '--key', required=True, help='Key column for comparison')
    p_diff.add_argument('-f', '--format', default='text', choices=['text', 'json'], help='Output format')
    
    p_split_file = subparsers.add_parser('split-file', help='Split CSV into multiple files by column')
    p_split_file.add_argument('file', help='Input CSV file')
    p_split_file.add_argument('column', help='Column to split by')
    
    args = parser.parse_args()
    
    if args.command == 'head':
        cmd_head(args)
    elif args.command == 'tail':
        cmd_tail(args)
    elif args.command == 'columns':
        cmd_columns(args)
    elif args.command == 'count':
        cmd_count(args)
    elif args.command == 'select':
        cmd_select(args)
    elif args.command == 'rename':
        cmd_rename(args)
    elif args.command == 'reorder':
        cmd_reorder(args)
    elif args.command == 'where':
        cmd_where(args)
    elif args.command == 'sort':
        cmd_sort(args)
    elif args.command == 'unique':
        cmd_unique(args)
    elif args.command == 'sample':
        cmd_sample(args)
    elif args.command == 'mutate':
        cmd_mutate(args)
    elif args.command == 'fill':
        cmd_fill(args)
    elif args.command == 'split':
        cmd_split_col(args)
    elif args.command == 'merge':
        cmd_merge_cols(args)
    elif args.command == 'groupby':
        cmd_groupby(args)
    elif args.command == 'pivot':
        cmd_pivot(args)
    elif args.command == 'describe':
        cmd_describe(args)
    elif args.command == 'join':
        cmd_join(args)
    elif args.command == 'concat':
        cmd_concat(args)
    elif args.command == 'diff':
        cmd_diff(args)
    elif args.command == 'split-file':
        cmd_split_file(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()