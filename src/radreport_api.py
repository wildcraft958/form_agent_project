# src/radreport_api.py
import requests
import json
from typing import Dict, List, Optional, Any, Union

class RadReportAPI:
    """
    Class to interact with the RadReport.org API for retrieving radiology report templates.
    """
    
    BASE_URL = "https://api3.rsna.org/radreport/v1"
    
    def __init__(self):
        """Initialize the RadReportAPI class."""
        self.session = requests.Session()
    
    def get_templates(self, 
                     specialty: Optional[str] = None,
                     organization: Optional[str] = None,
                     language: Optional[str] = None,
                     approved: bool = False,
                     search: Optional[str] = None,
                     sort: Optional[str] = None,
                     order: Optional[str] = None,
                     page: Optional[int] = None,
                     limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Get available templates from RadReport.org.
        
        Args:
            specialty: Two character value, multiple values supported with , delimiter
            organization: Alphabetic value, multiple values supported with , delimiter
            language: Data to sort on. title, created, language, etc.
            approved: Boolean, default False
            search: Alphabetic value, no default value
            sort: Data to sort on. title, created, language, etc.
            order: asc or desc
            page: Numeric value, no default
            limit: Numeric value, default to return all templates
            
        Returns:
            Dict containing template information
        """
        url = f"{self.BASE_URL}/templates"
        params = {}
        
        if specialty:
            params['specialty'] = specialty
        if organization:
            params['organization'] = organization
        if language:
            params['language'] = language
        if approved:
            params['approved'] = 'true'
        if search:
            params['search'] = search
        if sort:
            params['sort'] = sort
        if order:
            params['order'] = order
        if page:
            params['page'] = page
        if limit:
            params['limit'] = limit
            
        response = self.session.get(url, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()
    
    def get_template_details(self, template_id: Union[str, int], version: Optional[str] = None) -> Dict[str, Any]:
        """
        Get template details from RadReport.org.
        
        Args:
            template_id: Numeric value. Id's can be found in return of templates query
            version: Time stamp of previous version of template
            
        Returns:
            Dict containing template details
        """
        url = f"{self.BASE_URL}/templates/details/{template_id}"
        params = {}
        
        if version:
            params['version'] = version
            
        response = self.session.get(url, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()
    
    def get_subspecialties(self) -> Dict[str, Any]:
        """
        Get list of subspecialties from RadReport.org.
        
        Returns:
            Dict containing subspecialty information
        """
        url = f"{self.BASE_URL}/subspecialty/"
        
        response = self.session.get(url)
        
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()
    
    def get_organizations(self) -> Dict[str, Any]:
        """
        Get list of organizations from RadReport.org.
        
        Returns:
            Dict containing organization information
        """
        url = f"{self.BASE_URL}/organization"
        
        response = self.session.get(url)
        
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()
    
    def get_languages(self) -> Dict[str, Any]:
        """
        Get list of languages from RadReport.org.
        
        Returns:
            Dict containing language information
        """
        url = f"{self.BASE_URL}/language"
        
        response = self.session.get(url)
        
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()
