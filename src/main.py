import re
import graphql
import logger
import test
from datetime import datetime
import logging
import config

def release_based_on_duedate():
    if config.is_enterprise:
        issues = graphql.get_project_issues(
            owner=config.repository_owner,
            owner_type=config.repository_owner_type,
            project_number=config.project_number,
            duedate_field_name=config.duedate_field_name,
            filters={'open_only': True}
        )
    else:
        issues = graphql.get_repo_issues(
            owner=config.repository_owner,
            repository=config.repository_name,
            duedate_field_name=config.duedate_field_name
        )

    if not issues:
        logging.info('No issues have been found')
        return

    # Get the project_id, release_field_id 
    project_title = 'Test'
    project_id = graphql.get_project_id_by_title(
        owner=config.repository_owner, 
        project_title=project_title
    )

    if not project_id:
        logging.error(f"Project {project_title} not found.")
        return None
    
    release_field_id = graphql.get_release_field_id(
        project_id=project_id,
        release_field_name=config.release_field_name
    )

    if not release_field_id:
        logging.error(f"Release field not found in project {project_title}")
        return None

    release_options = graphql.get_release_field_options(project_id)
    if not release_options:
        logging.error("Failed to fetch release options.")
        return

    for project_item in issues:
        if project_item.get('state') == 'CLOSED':
            continue

        issue_content = project_item.get('content', {})
        if not issue_content:
            continue

        issue_id = issue_content.get('id')
        if not issue_id:
            continue

        due_date = project_item.get('fieldValueByName', {}).get(config.duedate_field_name)
        if not due_date:
            logging.info(f"No due date for issue {project_item.get('title')}. Skipping.")
            continue

        try:
            # Parse the due date
            due_date_obj = datetime.strptime(due_date, "%Y-%m-%d").date()
            logging.info(f"The due date is: {due_date_obj}")

            # Loop over release options and check if the release name contains a date range
            release_to_update = None
            for release_name, release_data in release_options.items():
                # If the release date is missing or incomplete, try to infer it from the release name
                start_date, end_date = parse_release_date(release_name, due_date_obj)

                if start_date and end_date:
                    if start_date <= due_date_obj <= end_date:
                        release_to_update = release_data
                        break  # Exit the loop once we find the matching release

            if release_to_update:
                logging.info(f"Due date for issue {project_item.get('title')} is {due_date_obj}. Changing release...")

                item_found = False
                for item in graphql.get_project_items(project_id):
                    if item.get('content') and item['content'].get('id') == issue_id:
                        item_id = item['id']
                        item_found = True
                        
                        logging.info(f"Proceeding to update the release")

                        updated = graphql.update_issue_release(
                            owner=config.repository_owner,
                            project_title=project_title,
                            project_id=project_id,
                            release_field_id=release_field_id,
                            item_id=item_id,
                            release_option_id=release_to_update['id']
                        )
                        if updated:
                            logging.info(f"Successfully updated issue {issue_id} to the release option.")
                        else:
                            logging.error(f"Failed to update issue {issue_id}.")
                        break  # Break out of the loop once updated
                    
                if not item_found:
                    logging.warning(f'No matching item found for issue ID: {issue_id}.')
                    continue  # Skip the issue as it cannot be updated
                    
        except (ValueError, TypeError) as e:
            logging.error(f"Failed to parse due date for issue {project_item.get('title')}. Error: {e}")
            continue

def main():
    logging.info('Process started...')
    if config.dry_run:
        logging.info('DRY RUN MODE ON!')

    # Notify about due date changes and release updates
    release_based_on_duedate()

if __name__ == "__main__":
    main()
