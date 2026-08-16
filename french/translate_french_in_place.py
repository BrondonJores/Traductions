import os
import re
import time
from deep_translator import GoogleTranslator

base_dir = r"c:\Users\HOUAKEU\Documents\Paradox Interactive\Victoria 3\mod\Victoria-3-Cold-War-Era-Mod-CWE-master\localization"
eng_dir = os.path.join(base_dir, "english")
fr_dir = os.path.join(base_dir, "french")

translator = GoogleTranslator(source='en', target='fr')

mapping = {
    '00_CWE_states_l_english.yml':             'CWE_states_l_french.yml',
    '0_buildings_l_english.yml':             '0_buildings_l_french.yml',
    '0_countries_l_english.yml':             '0_countries_l_french.yml',
    '0_cwe_music_l_english.yml':            '0_cwe_music_l_french.yml',
    '0_events_je_l_english.yml':             '0_events_je_l_french.yml',
    '0_general_l_english.yml':               '0_general_l_french.yml',
    '0_governments_l_english.yml':           '0_governments_l_french.yml',
    '0_ideologies_l_english.yml':            '0_ideologies_l_french.yml',
    '0_institutions_l_english.yml':          '0_citizen_institutions_l_french.yml',
    '0_interest_group_traits_l_english.yml': '0_interest_group_traits_l_french.yml',
    '0_interest_groups_l_english.yml':       '0_interest_groups_l_french.yml',
    '0_laws_l_english.yml':                  '0_laws_l_french.yml',
    '0_leaders_l_english.yml':               '0_leaders_l_french.yml',
    '0_legitimacy_levels_l_english.yml':     '0_legitimacy_levels_l_french.yml',
    '0_parties_l_english.yml':              '0_parties_l_french.yml',
    '0_political_institutions_l_english.yml':'0_political_institutions_l_french.yml',
    '0_religion_l_english.yml':             '0_religion_l_french.yml',
    '0_techs_l_english.yml':               '0_techs_l_french.yml',
    'country_flavor_text_l_english.yml':     'country_flavor_text_l_french.yml',
    'dynamic_country_names_l_english.yml':   'dynamic_countrry_names_l_french.yml',
}

TOKEN_PATTERN = r'\[.*?\]|@\w+!|#\w+|#!|\$.*?\$|\\n'

def mask_tokens(text):
    if not text or not text.strip():
        return text, []
    tokens = re.findall(TOKEN_PATTERN, text)
    masked_text = text
    for i, token in enumerate(tokens):
        masked_text = masked_text.replace(token, f'__TOK{i}__', 1)
    return masked_text, tokens

def unmask_tokens(translated_text, tokens):
    if not translated_text:
        return ""
    result = translated_text
    for i, token in enumerate(tokens):
        marker = f'__TOK{i}__'
        result = result.replace(marker, token)
        result = result.replace(f'__ TOK{i} __', token)
        result = result.replace(f'__ TOK{i}__', token)
        result = result.replace(f'__TOK{i} __', token)
        result = result.replace(f'_ _ TOK{i} _ _', token)
        result = result.replace(f'_ _TOK{i}_ _', token)
    return result

def safe_translate_batch(batch):
    if not batch:
        return []
    try:
        return translator.translate_batch(batch)
    except Exception as e:
        print(f"    Batch fallback ({e})...", flush=True)
        res = []
        for item in batch:
            try:
                t = translator.translate(item)
                res.append(t if t else item)
            except Exception:
                res.append(item)
            time.sleep(0.05)
        return res

def parse_yaml_entries(filepath):
    """Returns list of lines and dict key -> (line_index, ver, indent, val)"""
    lines = []
    keys = {}
    if not os.path.exists(filepath):
        return lines, keys
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        for i, line in enumerate(f):
            lines.append(line)
            m = re.match(r'^(\s*)([\w.\-]+)\s*:\s*(\d*)\s*"(.*)"\s*$', line.rstrip('\r\n'))
            if m:
                indent, key, ver, val = m.groups()
                keys[key] = (i, ver, indent, val)
    return lines, keys

def translate_file_in_place(eng_filename, fr_filename):
    eng_path = os.path.join(eng_dir, eng_filename)
    fr_path = os.path.join(fr_dir, fr_filename)

    if not os.path.exists(eng_path) or not os.path.exists(fr_path):
        return

    eng_lines, eng_keys = parse_yaml_entries(eng_path)
    fr_lines, fr_keys = parse_yaml_entries(fr_path)

    # Find keys in French file that match English values (untranslated)
    to_translate_items = [] # (key, line_idx, ver, indent, val, tokens)
    masked_texts = []

    for key, (fr_line_idx, ver, indent, fr_val) in fr_keys.items():
        if key in eng_keys:
            _, _, _, eng_val = eng_keys[key]
            # If French value equals English value and contains real text
            if fr_val == eng_val and eng_val.strip():
                # Check if it contains alphabetic text to translate
                cleaned = re.sub(TOKEN_PATTERN, '', eng_val).strip()
                if re.search(r'[a-zA-Z]{2,}', cleaned):
                    masked, tokens = mask_tokens(eng_val)
                    to_translate_items.append((key, fr_line_idx, ver, indent, eng_val, tokens))
                    masked_texts.append(masked)

    print(f"\n--- Translating {fr_filename} ({len(to_translate_items)} untranslated keys) ---", flush=True)

    if not to_translate_items:
        print(f"All keys in {fr_filename} are already translated!", flush=True)
        return

    chunk_size = 50
    total_chunks = (len(masked_texts) + chunk_size - 1) // chunk_size
    translated_results = []

    for idx in range(0, len(masked_texts), chunk_size):
        chunk = masked_texts[idx:idx+chunk_size]
        print(f"  Batch {idx//chunk_size + 1}/{total_chunks} ({len(chunk)} keys)...", flush=True)
        tr_chunk = safe_translate_batch(chunk)
        translated_results.extend(tr_chunk)
        time.sleep(0.1)

    # Update fr_lines in-place
    for (key, line_idx, ver, indent, _, tokens), tr_masked in zip(to_translate_items, translated_results):
        final_val = unmask_tokens(tr_masked, tokens)
        final_val = re.sub(r'(?<!\\)"', r'\"', final_val)
        ver_str = f":{ver}" if ver != "" else ":"
        indent_str = indent if indent else "    "
        fr_lines[line_idx] = f'{indent_str}{key}{ver_str} "{final_val}"\n'

    # Save updated file
    with open(fr_path, 'w', encoding='utf-8-sig') as f:
        f.writelines(fr_lines)

    print(f"Saved translated {fr_filename} successfully!", flush=True)

if __name__ == "__main__":
    start_time = time.time()
    for eng_file, fr_file in mapping.items():
        translate_file_in_place(eng_file, fr_file)
    print(f"\n==========================================")
    print(f"TRANSLATION FINISHED IN {time.time()-start_time:.1f}s!")
    print(f"==========================================")
