from logger import logger
import logging
import json
import requests
import config
import graphql

def check_comment_exists(issue_id, comment_text):
    """Check if the comment already exists on the issue."""
    comments = graphql.get_issue_comments(issue_id)
    for comment in comments:
        if comment_text in comment.get('body', ''):
            return True
    return False

def notify_change_status():
    # Fetch issues based on whether it's an enterprise or not
    if config.is_enterprise:
        issues = graphql.get_project_issues(
            owner=config.repository_owner,
            owner_type=config.repository_owner_type,
            project_number=config.project_number,
            status_field_name=config.status_field_name,
            filters={'open_only': True}
        )
    else:
        issues = graphql.get_repo_issues(
            owner=config.repository_owner,
            repository=config.repository_name,
            status_field_name=config.status_field_name
        )

    if not issues:
        logger.info('No issues have been found')
        return

    #----------------------------------------------------------------------------------------
    # Get the project_id, status_field_id and status_option_id 
    #----------------------------------------------------------------------------------------

    project_title = 'Requests Product Backlog'
    
    project_id = graphql.get_project_id_by_title(
        owner=config.repository_owner, 
        project_title=project_title
    )

    # logger.info(f'Printing the project_id: {project_id}')

    if not project_id:
        logging.error(f"Project {project_title} not found.")
        return None
    
    status_field_id = graphql.get_status_field_id(
        project_id=project_id,
        status_field_name=config.status_field_name
    )

    # logger.info(f"Printing the status_field_id: {status_field_id}")

    if not status_field_id:
        logging.error(f"Status field not found in project {project_title}")
        return None

    status_option_id = graphql.get_qatesting_status_option_id(
        project_id=project_id,
        status_field_name=config.status_field_name
    )

    #----------------------------------------------------------------------------------------

    items = graphql.get_project_items(
        owner=config.repository_owner, 
        owner_type=config.repository_owner_type,
        project_number=config.project_number,
        status_field_name=config.status_field_name
    )

    # Log fetched project items
    # logger.info(f'Fetched project items: {json.dumps(items, indent=4)}')

    for issue in issues:
        # Skip the issues if they are closed
        if issue.get('state') == 'CLOSED':
            continue

        # Print the issue object for debugging
        # print("Issue object: ", json.dumps(issue, indent=4))

        # Ensure the issue contains content
        issue_content = issue.get('content', {})
        if not issue_content:
            continue

        issue_id = issue_content.get('id')
        if not issue_id:
            continue

        # Debugging output for the issue
        # logger.info("Issue object: %s", json.dumps(issue, indent=4))

        # Safely get the fieldValueByName and current status
        field_value = issue.get('fieldValueByName')
        current_status = field_value.get('name') if field_value else None
        # logger.info(f'The current status of {issue_id} is: {current_status}')

        comment_text = "This issue is ready for testing. Please proceed accordingly in 15 minutes."

        if current_status == 'QA Testing':
            continue # skip the issue 

        if check_comment_exists(issue_id, comment_text):
            continue # skip the issue if it was in QA Testing before (the comment already exists)
            
        issue_title = issue.get('title')

        has_merged_pr = graphql.get_issue_has_merged_pr(issue_id)
        if has_merged_pr:  
            
            print("Issue object: ", json.dumps(issue, indent=4))

            logger.info(f'Proceeding to update the status to QA Testing as it contains a merged PR.')

            # Find the item id for the issue
            item_found = False
            for item in items:
                if item.get('content') and item['content'].get('id') == issue_id:
                    item_id = item['id']
                    
                    item_found = True
                    
                    # Proceed to update the status

                    update_result = graphql.update_issue_status_to_qa_testing(
                        owner=config.repository_owner,
                        project_title=project_title,
                        project_id=project_id,
                        status_field_id=status_field_id,
                        item_id=item_id,
                        status_option_id=status_option_id
                    )
    
                    if update_result:
                        logger.info(f'Successfully updated issue {issue_id} to QA Testing.')
                    else:
                        logger.error(f'Failed to update issue {issue_id}.')
                    break  # Break out of the loop once updated

            if not item_found:
                logger.warning(f'No matching item found for issue ID: {issue_id}.')
                continue #  Skip the issue as it cannot be updated

                
def main():
    logger.info('Process started...')
    if config.dry_run:
        logger.info('DRY RUN MODE ON!')

    notify_change_status()

if __name__ == "__main__":
    main()
