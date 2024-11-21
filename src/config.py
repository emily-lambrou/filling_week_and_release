import os

repository_owner = os.environ['GITHUB_REPOSITORY_OWNER']
repository_owner_type = os.environ['INPUT_REPOSITORY_OWNER_TYPE']
repository = os.environ['GITHUB_REPOSITORY']
repository_name = repository.split('/')[1]
server_url = os.environ['GITHUB_SERVER_URL']
is_enterprise = True if os.environ.get('INPUT_ENTERPRISE_GITHUB') == 'True' else False
dry_run = True if os.environ.get('INPUT_DRY_RUN') == 'True' else False

gh_token = os.environ['INPUT_GH_TOKEN']
project_number = int(os.environ['INPUT_PROJECT_NUMBER'])
project_title = os.environ['INPUT_PROJECT_TITLE']
api_endpoint = os.environ.get('GITHUB_GRAPHQL_URL', 'https://github.intranet.unicaf.org/api/graphql')
duedate_field_name = os.environ['INPUT_DUEDATE_FIELD_NAME']
release_field_name = os.environ['INPUT_RELEASE_FIELD_NAME']
week_field_name = os.environ['INPUT_WEEK_FIELD_NAME']
