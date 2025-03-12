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
    return template.replace(placeholder, content)

# Guardar el documento actualizado
def save_updated_document(updated_template: str, output_file: str):
    with open(output_file, "w",  encoding='utf-8') as file:
        file.write(updated_template)

# API para manejar solicitudes del usuario
def update_latex_section(section, content, filename):
    generated_file = f"generatedDocuments/{filename}.tex"
    template = load_template(generated_file)
    updated_template = edit_section(template, section, content)
    save_updated_document(updated_template, generated_file)
    print(f"File updated with section {section} and content {content}")
    return "Sección actualizada con éxito"
