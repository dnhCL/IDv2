from openai import OpenAI
import os
from assistant_instructions import instructions
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.environ['OPEN_AI_API_KEY']

client = OpenAI(api_key=OPENAI_API_KEY)


# Function to create a vector store and upload files
def create_vector_store_with_files(paths):
    # Creating the vector store
    vector_store_response = client.beta.vector_stores.create(name="Invention_files") # In case of need
    vector_store_id = vector_store_response.id

    # Upload files and associate them with the vector store
    for path in paths:
        with open(path, "rb") as file:
            # Update the purpose to 'assistants' from 'vector-search'
            file_response = client.files.create(file=file, purpose="assistants")
            client.beta.vector_stores.files.create(vector_store_id=vector_store_id, file_id=file_response.id)

    return vector_store_id


# Function to create or update the assistant
def create_or_update_assistant(file_paths):
    assistant_name = "ID1"#"InventionDisclosureAssistant"
    vector_store_id = create_vector_store_with_files(file_paths)
    # Retrieve list of existing assistants
    existing_assistants = client.beta.assistants.list().data
    existing_assistant = next(
        (a for a in existing_assistants if a.name == assistant_name), None)

    # Define tools including the new action tool
    tools = [
        {"type": "file_search"},
        {
            "type": "function",
            "function": {
                "name": "modify_document",
                "description": "Modify the latex document on the section specified by user",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "Section": {
                            "type": "string",
                            "description": "The section which the user wants to edit on the investigation disclosure. The section ouput should be one of the followings:  TITLE, RESEARCHER, PURPOSE, DETAILED_DESCRIPTION, STATE_OF_THE_ART, CONCEPTION, PREVIOUS_DISCLOSURE, DEVELOPMENT, PROGRAM_CONTRACT, WITNESSES, RELEVANT_INFO"
                        },
                        "Content": {
                            "type": "string",
                            "description": "The content generated related to the section specified by the user.",
                        },
                    },
                    "required": ["Section", "Content"]
                }
            }
        }
    ]

    if existing_assistant:
        assistant_id = existing_assistant.id
        # Update the existing assistant
        updated_assistant = client.beta.assistants.update(
            assistant_id=assistant_id,
            instructions=instructions,
            tools=tools,
            tool_resources={
                "file_search": {
                    "vector_store_ids": [vector_store_id]
                }
            })
        print(f"Updated existing assistant: {assistant_name}")
        return updated_assistant
    else:
        # Create a new assistant
        new_assistant = client.beta.assistants.create(name=assistant_name,
                                                      instructions=instructions,
                                                      model="gpt-3.5-turbo-0125",
                                                      tools=tools,
                                                      #tool_choice="auto",
                                                      tool_resources={
                                                        "file_search": {
                                                            "vector_store_ids": [vector_store_id]
                                                            }
                                                        })
        print(f"Created new assistant: {assistant_name}")
        return new_assistant