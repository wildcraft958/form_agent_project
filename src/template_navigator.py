# src/template_navigator.py
from typing import Dict, List, Optional, Any, Union
import inquirer
from src.radreport_api import RadReportAPI
from src.database import templates.json

class TemplateNavigator:
    """
    Class to help navigate and select templates from RadReport.org.
    """
    
    def __init__(self, api: RadReportAPI):
        """
        Initialize the TemplateNavigator class.
        
        Args:
            api: RadReportAPI instance
        """
        self.api = api
        
    def navigate_templates(self) -> Dict[str, Any]:
        """
        Guide the user through template selection.
        
        Returns:
            Selected template details
        """
        # Ask if user wants to navigate by parameters or directly provide ID
        choices = [
            'Navigate through parameters',
            'Provide template ID directly'
        ]
        
        questions = [
            inquirer.List('choice',
                          message="How would you like to select a template?",
                          choices=choices)
        ]
        
        answers = inquirer.prompt(questions)
        
        if answers['choice'] == 'Navigate through parameters':
            return self._navigate_by_parameters()
        else:
            return self._get_by_id()
    
    def _navigate_by_parameters(self) -> Dict[str, Any]:
        """
        Navigate templates by filtering through parameters.
        
        Returns:
            Selected template details
        """
        # Start with selecting parameter type
        param_choices = [
            'Specialty',
            'Organization',
            'Language',
            'Search term',
            'Skip filtering (show all)'
        ]
        
        questions = [
            inquirer.List('param_type',
                          message="Select a parameter to filter templates:",
                          choices=param_choices)
        ]
        
        param_answers = inquirer.prompt(questions)
        
        # Apply the selected filter
        filter_params = {}
        
        if param_answers['param_type'] == 'Specialty':
            specialties = self.api.get_subspecialties()
            specialty_choices = [
                (f"{s['name']} ({s['code']})", s['code']) for s in specialties['data']
            ]
            
            questions = [
                inquirer.Checkbox('specialties',
                                 message="Select specialties (use space to select, enter to confirm):",
                                 choices=specialty_choices)
            ]
            
            specialty_answers = inquirer.prompt(questions)
            
            if specialty_answers['specialties']:
                filter_params['specialty'] = ','.join(specialty_answers['specialties'])
                
        elif param_answers['param_type'] == 'Organization':
            organizations = self.api.get_organizations()
            org_choices = [
                (f"{o['name']} ({o['code']})", o['code']) for o in organizations['data']
            ]
            
            questions = [
                inquirer.Checkbox('organizations',
                                 message="Select organizations (use space to select, enter to confirm):",
                                 choices=org_choices)
            ]
            
            org_answers = inquirer.prompt(questions)
            
            if org_answers['organizations']:
                filter_params['organization'] = ','.join(org_answers['organizations'])
                
        elif param_answers['param_type'] == 'Language':
            languages = self.api.get_languages()
            lang_choices = [
                (f"{l['name']} ({l['code']})", l['code']) for l in languages['data']
            ]
            
            questions = [
                inquirer.Checkbox('languages',
                                 message="Select languages (use space to select, enter to confirm):",
                                 choices=lang_choices)
            ]
            
            lang_answers = inquirer.prompt(questions)
            
            if lang_answers['languages']:
                filter_params['language'] = ','.join(lang_answers['languages'])
                
        elif param_answers['param_type'] == 'Search term':
            questions = [
                inquirer.Text('search',
                             message="Enter search term:")
            ]
            
            search_answers = inquirer.prompt(questions)
            
            if search_answers['search']:
                filter_params['search'] = search_answers['search']
        
        # Ask for limit to make the list manageable
        questions = [
            inquirer.Text('limit',
                         message="Enter maximum number of templates to display (default is 20):",
                         default="20")
        ]
        
        limit_answers = inquirer.prompt(questions)
        
        try:
            filter_params['limit'] = int(limit_answers['limit'])
        except ValueError:
            filter_params['limit'] = 20
            
        # Get templates with filters
        templates = self.api.get_templates(**filter_params)
        
        if not templates.get('data') or len(templates['data']) == 0:
            print("No templates found with the selected filters.")
            return self._navigate_by_parameters()  # Try again
            
        # Present templates for selection
        template_choices = [
            (f"{t['title']} (ID: {t['id']})", t['id']) for t in templates['data']
        ]
        
        questions = [
            inquirer.List('template_id',
                         message="Select a template:",
                         choices=template_choices)
        ]
        
        template_answers = inquirer.prompt(questions)
        
        # Get the selected template details
        return self.api.get_template_details(template_answers['template_id'])
    
    def _get_by_id(self) -> Dict[str, Any]:
        """
        Get template by directly providing ID.
        
        Returns:
            Template details
        """
        questions = [
            inquirer.Text('template_id',
                         message="Enter template ID:")
        ]
        
        id_answers = inquirer.prompt(questions)
        
        try:
            return self.api.get_template_details(id_answers['template_id'])
        except Exception as e:
            print(f"Error retrieving template: {str(e)}")
            return self._get_by_id()  # Try again
