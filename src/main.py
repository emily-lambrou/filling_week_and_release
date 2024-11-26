import re
import graphql
import logger
import test
from datetime import datetime
import logging
import config

# Regex pattern for validating release name format (e.g., includes date range)
RELEASE_DATE_PATTERN = r"([a-zA-Z]+ \d{2}) - ([a-zA-Z]+ \d{2}), (\d{4})(?: \(\S+\))?"

def is_valid_release_format(release_name):
    """
    Validates the format of a release name to check for expected date ranges.
    """
    return re.search(RELEASE_DATE_PATTERN, release_name) is not None

def find_matching_release(release_options, due_date_obj):
    """
    Find the correct release based on the due date.
    :param release_options: Dictionary of release options with date ranges
    :param due_date_obj: The due date to match as a datetime object
    :return: Matching release option or None
    """
    for release_name, release_data in release_options.items():
        # Skip invalid releases (if the format is not valid)
        if not is_valid_release_format(release_name):
            logging.warning(f"Skipping release due to invalid format: {release_name}")
            continue

        # Check if the release date range matches the due date
        start_date = datetime.strptime(release_data['start_date'], "%b %d, %Y").date()
        end_date = datetime.strptime(release_data['end_date'], "%b %d, %Y").date()
        
        if start_date <= due_date_obj <= end_date:
            return release_data
    return None

def parse_release_date(release_name, due_date_obj):
    """
    Parses a release date and handles cases where the year is missing for the start or end date.
    :param release_name: The release name (e.g., "Jan 07 - Feb 09")
    :param due_date_obj: The due date as a datetime object to infer the year from
    :return: Start and end dates as datetime.date objects
    """
    # Find date ranges in the release name (e.g., "Jan 07 - Feb 09")
    match = re.search(r'([a-zA-Z]+ \d{2}) - ([a-zA-Z]+ \d{2}), (\d{4})(?: \(\S+\))?', release_name)
    
    if match:
        start_date_str, end_date_str, year = match.groups()

        # Add the year from the matched group to the start and end dates
        start_date_month_day = datetime.strptime(start_date_str, "%b %d")
        end_date_month_day = datetime.strptime(end_date_str, "%b %d")
        
        start_date = datetime(year=int(year), month=start_date_month_day.month, day=start_date_month_day.day).date()
        end_date = datetime(year=int(year), month=end_date_month_day.month, day=end_date_month_day.day).date()

        return start_date, end_date

    else:
        # If no date range found, return None or handle as necessary
        return None, None

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
         
        # Get the due date value
        due_date = None
        due_date_obj = None
        try:
            due_date = project_item.get('fieldValueByName', {}).get('date')
            if due_date:
                due_date_obj = datetime.strptime(due_date, "%Y-%m-%d").date()
                logging.info(f"Due date is: {due_date_obj}.")
        except (AttributeError, ValueError) as e:
            continue  # Skip this issue and move to the next

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
