import requests
import json
import os
from urllib.parse import quote

class RadReportAPI:
    """
    Handler for interacting with the RadReport.org REST API.
    Provides methods to fetch templates and template details.
    """
    
    def __init__(self):
        """Initialize the RadReport API client."""
        self.base_url = "https://api3.rsna.org/radreport/v1"
        self.cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def get_templates(self, specialty=None, organization=None, language=None, 
                      approved=True, search=None, sort=None, order=None, 
                      page=None, limit=None, use_cache=True):
        """
        Fetch available templates from RadReport.org based on provided filters.
        
        Args:
            specialty (str): Comma-separated specialty codes (e.g., "CH,CT")
            organization (str): Comma-separated org codes (e.g., "rsna,acr")
            language (str): Comma-separated language codes (e.g., "en,fr")
            approved (bool): Filter for approved templates only
            search (str): Search term for template titles
            sort (str): Field to sort on (e.g., "title", "created")
            order (str): Sort order ("asc" or "desc")
            page (int): Page number for pagination
            limit (int): Limit number of results
            use_cache (bool): Whether to use cached results if available
            
        Returns:
            dict: JSON response containing template list or error message
        """
        endpoint = f"{self.base_url}/templates"
        
        # Build parameters
        params = {}
        if specialty:
            params['specialty'] = specialty
        if organization:
            params['organization'] = organization
        if language:
            params['language'] = language
        if approved is not None:
            params['approved'] = str(approved).lower()
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
            
        # Build cache key
        cache_key = f"templates_{json.dumps(params, sort_keys=True)}.json"
        cache_path = os.path.join(self.cache_dir, cache_key)
        
        # Check cache first
        if use_cache and os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Cache error: {e}. Fetching from API...")
        
        # Make API request
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            result = response.json()
            
            # Save to cache
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
                
            return result
        except requests.exceptions.RequestException as e:
            print(f"API request error: {e}")
            return {"error": str(e)}
    
    def get_template_details(self, template_id, version=None, use_cache=True):
        """
        Fetch details for a specific template.
        
        Args:
            template_id (int): Template ID
            version (str): Optional version timestamp
            use_cache (bool): Whether to use cached results if available
            
        Returns:
            dict: JSON response containing template details or error message
        """
        # Build endpoint
        endpoint = f"{self.base_url}/templates/details/{template_id}"
        
        # Build parameters
        params = {}
        if version:
            params['version'] = version
            
        # Build cache key
        cache_key = f"template_{template_id}"
        if version:
            cache_key += f"_v_{quote(version, safe='')}"
        cache_key += ".json"
        cache_path = os.path.join(self.cache_dir, cache_key)
        
        # Check cache first
        if use_cache and os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Cache error: {e}. Fetching from API...")
        
        # Make API request
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            result = response.json()
            
            # Save to cache
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
                
            return result
        except requests.exceptions.RequestException as e:
            print(f"API request error: {e}")
            return {"error": str(e)}
    
    def get_subspecialties(self, use_cache=True):
        """
        Fetch available subspecialties.
        
        Args:
            use_cache (bool): Whether to use cached results if available
            
        Returns:
            dict: JSON response containing subspecialties or error message
        """
        endpoint = f"{self.base_url}/subspecialty"
        
        # Build cache key
        cache_key = "subspecialties.json"
        cache_path = os.path.join(self.cache_dir, cache_key)
        
        # Check cache first
        if use_cache and os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Cache error: {e}. Fetching from API...")
        
        # Make API request
        try:
            response = requests.get(endpoint)
            response.raise_for_status()
            result = response.json()
            
            # Save to cache
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
                
            return result
        except requests.exceptions.RequestException as e:
            print(f"API request error: {e}")
            return {"error": str(e)}
    
    def get_organizations(self, use_cache=True):
        """
        Fetch available organizations.
        
        Args:
            use_cache (bool): Whether to use cached results if available
            
        Returns:
            dict: JSON response containing organizations or error message
        """
        endpoint = f"{self.base_url}/organization"
        
        # Build cache key
        cache_key = "organizations.json"
        cache_path = os.path.join(self.cache_dir, cache_key)
        
        # Check cache first
        if use_cache and os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Cache error: {e}. Fetching from API...")
        
        # Make API request
        try:
            response = requests.get(endpoint)
            response.raise_for_status()
            result = response.json()
            
            # Save to cache
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
                
            return result
        except requests.exceptions.RequestException as e:
            print(f"API request error: {e}")
            return {"error": str(e)}
    
    def get_languages(self, use_cache=True):
        """
        Fetch available languages.
        
        Args:
            use_cache (bool): Whether to use cached results if available
            
        Returns:
            dict: JSON response containing languages or error message
        """
        endpoint = f"{self.base_url}/language"
        
        # Build cache key
        cache_key = "languages.json"
        cache_path = os.path.join(self.cache_dir, cache_key)
        
        # Check cache first
        if use_cache and os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Cache error: {e}. Fetching from API...")
        
        # Make API request
        try:
            response = requests.get(endpoint)
            response.raise_for_status()
            result = response.json()
            
            # Save to cache
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
                
            return result
        except requests.exceptions.RequestException as e:
            print(f"API request error: {e}")
            return {"error": str(e)}
    
    def convert_template_to_form_schema(self, template_details):
        """
        Convert RadReport template details to a form schema compatible with the form processor.
        
        Args:
            template_details (dict): Template details from the API
            
        Returns:
            dict: Form schema compatible with the form processor
        """
        if "error" in template_details:
            return {"error": template_details["error"]}
            
        form_schema = {}
        
        # Extract template metadata
        title = template_details.get("title", "Medical Form")
        description = template_details.get("description", "")
        
        # Add form metadata
        form_schema["_metadata"] = {
            "title": title,
            "description": description,
            "template_id": template_details.get("id"),
            "version": template_details.get("version"),
            "organization": template_details.get("organization")
        }
        
        # Extract form fields
        # This is a simplified example - actual implementation would need to parse
        # the template format which could be in HTML, XML, or some other format
        if "sections" in template_details:
            for section in template_details["sections"]:
                section_name = section.get("name", "")
                
                # Process fields in this section
                if "fields" in section:
                    for field in section["fields"]:
                        field_name = field.get("name", "").lower().replace(" ", "_")
                        if not field_name:
                            continue
                            
                        form_schema[field_name] = {
                            "type": field.get("type", "text"),
                            "label": field.get("name", field_name),
                            "value": "",
                            "required": field.get("required", False),
                            "section": section_name,
                            "description": field.get("description", ""),
                            "options": field.get("options", [])
                        }
        
        # If no structured sections/fields found, try direct fields
        elif "fields" in template_details:
            for field in template_details["fields"]:
                field_name = field.get("name", "").lower().replace(" ", "_")
                if not field_name:
                    continue
                    
                form_schema[field_name] = {
                    "type": field.get("type", "text"),
                    "label": field.get("name", field_name),
                    "value": "",
                    "required": field.get("required", False),
                    "description": field.get("description", ""),
                    "options": field.get("options", [])
                }
        
        # Extract fields from content as fallback
        else:
            content = template_details.get("content", "")
            # Simplified extraction - in practice would need more robust parsing
            import re
            field_pattern = r'\[(.*?)\]'
            matches = re.findall(field_pattern, content)
            
            for i, match in enumerate(matches):
                field_name = match.lower().replace(" ", "_")
                form_schema[field_name] = {
                    "type": "text",
                    "label": match,
                    "value": "",
                    "required": True
                }
        
        return form_schema