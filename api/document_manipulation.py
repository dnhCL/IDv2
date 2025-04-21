import os
import requests 
# Cargar la plantilla LaTeX



def load_template(filename):
    fallback_file = "invention-disclosure-structure.tex"
    try:
        with open(filename, "r", encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        print(f"{filename} no encontrado. Cargando archivo predeterminado.")
        with open(fallback_file, "r", encoding='utf-8') as fallback:
            return fallback.read()


# Editar una sección del documento
def edit_section(template: str, section: str, content: str) -> str:
    placeholder = f"<<{section}>>"
    if placeholder not in template:
        print(f"[edit_section] ❗ MARCADOR NO ENCONTRADO: {placeholder}")
    else:
        print(f"[edit_section] ✅ Reemplazando {placeholder}")
    return template.replace(placeholder, content)


# Guardar el documento actualizado
def save_updated_document(updated_template: str, output_file: str):
    with open(output_file, "w",  encoding='utf-8') as file:
        file.write(updated_template)



def update_latex_section(section_key: str, new_content: str, thread_id: str):
    """
    Inserta el contenido debajo del marcador <<SECTION_KEY>>, 
    y elimina cualquier contenido previamente insertado automáticamente.
    """
    file_path = f"generatedDocuments/{thread_id}.tex"
    marker = f"<<{section_key}>>"
    start_tag = f"% --- start:{section_key} ---"
    end_tag = f"% --- end:{section_key} ---"

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        updated_lines = []
        skip = False
        for line in lines:
            if start_tag in line:
                skip = True
                continue
            if end_tag in line:
                skip = False
                continue
            if skip:
                continue
            updated_lines.append(line)
            if marker in line:
                new_content = sanitize_latex_input(new_content)
                updated_lines.append(f"{start_tag}\n")
                updated_lines.append(new_content.strip() + "\n")
                updated_lines.append(f"{end_tag}\n")
                print(f"[edit_section] ✅ Reemplazado marcador {marker}")

        with open(file_path, 'w', encoding='utf-8') as file:
            file.writelines(updated_lines)

        requests.post("http://localhost:5000/compile", json={"thread_id": thread_id})
        print(f"[compile] ✅ Compilación solicitada para thread_id={thread_id}")

    except Exception as e:
        print(f"[edit_section] ⚠️ Error actualizando sección {section_key}: {e}")
        print(f"[compile] ❌ Error al solicitar compilación: {e}")





def sanitize_latex_input(text: str) -> str:
    """
    Escapa caracteres problemáticos para LaTeX.
    """
    replacements = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\^{}',
        '\\': r'\textbackslash{}'
    }

    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text

