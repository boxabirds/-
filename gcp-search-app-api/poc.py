# code heavily inspired by https://cloud.google.com/generative-ai-app-builder/docs/multi-turn-search#genappbuilder_multi_turn_search-python
from typing import List
from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine
import os
import argparse  # Import the argparse module

# Parse command line arguments
def parse_arguments():
    parser = argparse.ArgumentParser(description='Process conversation turns.')
    parser.add_argument('-q', '--questions', type=str, help='Conversation turns separated by commas', required=True)
    parser.add_argument('--conversation-id', type=str, help='Optional conversation ID to update', required=False)
    args = parser.parse_args()
    search_queries = [question.strip() for question in args.questions.split(',')]
    return search_queries, args.conversation_id

# TODO(developer): Uncomment these variables before running the sample.
project_id = os.environ["PYKAI_PROJECT_ID"]  # Your GCP Project ID
location = "global"                    # Values: "global", "us", "eu"
data_store_id = os.environ["PYKAI_DATA_STORE_ID"]  # Your Data Store ID

def multi_turn_search_sample(
    project_id: str,
    location: str,
    data_store_id: str,
    search_queries: List[str],
    conversation_id: str = None,
) -> List[discoveryengine.ConverseConversationResponse]:
    client_options = (
        ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
        if location != "global"
        else None
    )

    # Create a client
    client = discoveryengine.ConversationalSearchServiceClient(
        client_options=client_options
    )

    if conversation_id:
        conversation_name = client.conversation_path(project=project_id, location=location, data_store=data_store_id, conversation=conversation_id)
    else:
        conversation = client.create_conversation(
            parent=client.data_store_path(project=project_id, location=location, data_store=data_store_id),
            conversation=discoveryengine.Conversation(),
        )
        conversation_name = conversation.name
        print(f"Conversation ID: {conversation.name.split('/')[-1]}")

    for search_query in search_queries:
        request = discoveryengine.ConverseConversationRequest(
            name=conversation_name,
            query=discoveryengine.TextInput(input=search_query),
            serving_config=client.serving_config_path(
                project=project_id,
                location=location,
                data_store=data_store_id,
                serving_config="default_config",
            ),
            summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
                summary_result_count=3,
                include_citations=True,
            ),
        )
        response = client.converse_conversation(request)
        print(response)

if __name__ == "__main__":
    search_queries, conversation_id = parse_arguments()  # Updated to unpack conversation_id
    multi_turn_search_sample(project_id, location, data_store_id, search_queries, conversation_id)
