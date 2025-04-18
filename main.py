import os
import json
import re
import argparse
import time
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.traceback import install
from src.html_converter import convert_html_to_json
from src.JSON_converter import convert_json_to_html
from src.llm_handler import LLMHandler
from src.chat_history import ChatHistoryManager
from src.form_processor import FormProcessor
from src.context_generator import generate_context_for_chatbot
from src.text_to_speech import RealtimeTTSHandler
from src.live_stt import LiveSTT

# Enable rich tracebacks for better error visibility
install()
console = Console()

# Load environment variables
load_dotenv()

def read_latest_summary(summaries_dir):
    """Read the most recent summary file from the summaries directory."""
    try:
        summary_files = [f for f in os.listdir(summaries_dir) if f.endswith('_summary.txt')]
        if not summary_files:
            return None
        
        # Get the most recent summary file
        latest_summary = max(summary_files, key=lambda f: os.path.getmtime(os.path.join(summaries_dir, f)))
        summary_path = os.path.join(summaries_dir, latest_summary)
        
        with open(summary_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        console.print(Panel(f"[red]Error reading summary file: {str(e)}[/red]", title="Summary Error", border_style="red"))
        return None

def get_project_paths():
    """Get standardized project paths."""
    base_dir = os.path.abspath(os.path.dirname(__file__))
    samples_dir = os.path.join(base_dir, "samples")
    summaries_dir = os.path.join(base_dir, "summaries")
    models_dir = os.path.join(base_dir, "models")
    
    os.makedirs(summaries_dir, exist_ok=True)
    os.makedirs(models_dir, exist_ok=True)
    
    return {
        "base": base_dir,
        "samples": samples_dir,
        "summaries": summaries_dir,
        "history": os.path.join(base_dir, "chat_history.json"),
        "models": models_dir
    }

def read_html_file(file_path):
    """Read HTML file content with improved error handling."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        console.print(Panel(f"[red]Error: File not found at {file_path}[/red]", title="File Error", border_style="red"))
        return None
    except Exception as e:
        console.print(Panel(f"[red]Unexpected error reading file: {str(e)}[/red]", title="File Error", border_style="red"))
        return None

def save_json_to_file(json_data, file_path):
    """Save JSON data to file with directory creation."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)
        console.print(Panel(f"[green]Successfully saved JSON to {file_path}[/green]", title="Success", border_style="green"))
    except Exception as e:
        console.print(Panel(f"[red]Error saving JSON file: {str(e)}[/red]", title="File Error", border_style="red"))

def enhance_form_schema(form_json):
    """Enhance the form schema with additional metadata for better interaction."""
    enhanced_form = dict(form_json)
    critical_terms = ["diagnosis", "impression", "findings", "assessment"]
    
    for field_name in enhanced_form:
        if any(term in field_name.lower() for term in critical_terms):
            enhanced_form[field_name]["required"] = True
            
    return enhanced_form

# Modify setup_speech_components
def setup_speech_components(use_speech, tts_engine, whisper_model, language):
    tts_handler = None
    stt_handler = None
    if use_speech:
        # Initialize TTS
        console.print(Panel("[bold]Initializing Text-to-Speech...[/bold]", border_style="blue"))
        tts_handler = RealtimeTTSHandler(engine_type=tts_engine)
        
        # Initialize Whisper STT - FIXED PARAMETER NAME
        console.print(Panel("[bold]Initializing Whisper...[/bold]", border_style="blue"))
        try:
            # Changed parameter name from model_size to whisper_model
            stt_handler = LiveSTT(whisper_model=whisper_model)
            console.print(f"[green]Whisper {whisper_model} model loaded successfully[/green]")
        except Exception as e:
            console.print(Panel(f"[red]STT initialization failed: {str(e)}[/red]",
                        title="Error", border_style="red"))
            stt_handler = None
    return tts_handler, stt_handler

def process_form_with_speech(form_processor, tts_handler, stt_handler):
    """Process form using speech interface."""
    if not tts_handler or not stt_handler:
        console.print(Panel("[yellow]Speech components not available. Using text mode.[/yellow]", 
                          title="Warning", border_style="yellow"))
        return form_processor.process_form()
    
    # Initialize form with form context if available
    completed_form = dict(form_processor.form_data)
    
    # Start conversation with form context if available
    if form_processor.form_context:
        console.print(Panel(f"{form_processor.form_context}", title="Form Context", border_style="cyan"))
        tts_handler.speak(form_processor.form_context)
        
        # Add to chat history
        form_processor.chat_history.append({
            'user': '',
            'assistant': form_processor.form_context,
            'is_context': True
        })
        
    # Process each field iteratively with enhanced user interaction
    for field_name, field_data in form_processor.form_data.items():
        # Skip processing if field is hidden or system-managed
        if field_data.get('hidden', False) or field_name.startswith('_'):
            continue
            
        attempts = 0
        valid = False
        
        # Generate field prompt with examples and guidance
        field_prompt, last_exchanges = form_processor._create_interactive_field_prompt(field_name, field_data)
        
        while attempts < form_processor.max_attempts and not valid:
            # Display prompt to user (only on first attempt or if prompt changes)
            if attempts == 0:
                console.print(Panel(field_prompt, title="Bot", border_style="blue"))
                tts_handler.speak(field_prompt)
                
            # Get user input via speech
            console.print("[bold yellow]Listening for your response...[/bold yellow]")
            
            # Start listening for speech
            speech_result = []
            
            def on_speech_result(text):
                speech_result.append(text)
                console.print(f"[bold magenta]User:[/bold magenta] {text}")
                stt_handler.stop_listening()
            
            stt_handler.start_listening(on_speech_result)
            
            # Wait for speech input with timeout
            timeout = 30  # 30 seconds timeout
            start_time = time.time()
            user_input = ""
            
            while not speech_result and time.time() - start_time < timeout:
                time.sleep(0.1)
                
            # Stop listening if timeout reached
            if not speech_result:
                stt_handler.stop_listening()
                console.print("[yellow]No speech detected. Please type your response.[/yellow]")
                user_input = console.input("[bold magenta]User (text fallback):[/bold magenta] ")
            else:
                user_input = speech_result[0]
            
            # Check if user wants to skip optional field
            is_required = field_data.get('required', False)
            if not is_required and form_processor._is_skip_request(user_input):
                completed_form[field_name]['value'] = "Not specified"
                response = f"I've marked {form_processor._format_field_name(field_name)} as 'Not specified'. Moving on."
                console.print(Panel(response, border_style="cyan"))
                tts_handler.speak(response)
                
                form_processor.chat_history.append({
                    'user': user_input,
                    'assistant': response,
                    'field': field_name,
                    'value': "Not specified"
                })
                valid = True
                break
            
            # Save raw input in case validation fails
            raw_input = user_input
            
            # Validate with improved context awareness
            is_valid, validation_message, processed_value = form_processor._validate_input_with_context(
                field_name, field_data, user_input, last_exchanges
            )
            
            if is_valid:
                # Update the form with validated input
                completed_form[field_name]['value'] = processed_value
                
                # Add to chat history
                form_processor.chat_history.append({
                    'user': user_input,
                    'assistant': field_prompt,
                    'valid': True,
                    'field': field_name,
                    'value': processed_value
                })
                
                # Confirm the input with the user
                confirmation = f"I've recorded '{processed_value}' for {form_processor._format_field_name(field_name)}. Thank you."
                console.print(Panel(confirmation, border_style="green"))
                tts_handler.speak(confirmation)
                valid = True
            else:
                # Increment attempt counter
                attempts += 1
                
                # Show validation error with guidance for correction
                guidance = form_processor._generate_guidance(field_name, field_data, user_input, attempts)
                error_message = f"{validation_message} {guidance}"
                
                console.print(Panel(error_message, border_style="red"))
                tts_handler.speak(error_message)
                
                # Add failed attempt to chat history
                form_processor.chat_history.append({
                    'user': user_input,
                    'assistant': error_message,
                    'valid': False,
                    'field': field_name,
                    'error': validation_message
                })
                
        # If max attempts reached, accept the input but flag for review
        if not valid:
            acceptance_msg = "I'll accept your input and mark this for later review. Let's continue with the form."
            console.print(Panel(acceptance_msg, border_style="yellow"))
            tts_handler.speak(acceptance_msg)
            
            completed_form[field_name]['value'] = raw_input
            completed_form[field_name]['needs_review'] = True
            completed_form[field_name]['review_reason'] = "Maximum validation attempts reached"
            form_processor.needs_review.append(field_name)
            
            # Add to chat history
            form_processor.chat_history.append({
                'user': raw_input,
                'assistant': acceptance_msg,
                'valid': False,
                'field': field_name,
                'flagged': True
            })
            
    # Add review status to the completed form
    if form_processor.needs_review:
        completed_form['_review_status'] = {
            'fields_needing_review': form_processor.needs_review,
            'hidden': True
        }
        
    return completed_form

def main():
    """Main execution flow with enhanced error handling and user experience."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Medical Form Assistant with Speech Support")
    parser.add_argument("--speech", action="store_true", help="Enable speech interface")
    parser.add_argument("--tts-engine", choices=["system", "elevenlabs", "openai"], default="system",
                      help="Text-to-Speech engine to use")
    parser.add_argument("--stt-model", help="Path to DeepSpeech model file (.pbmm)")
    parser.add_argument("--stt-scorer", help="Path to DeepSpeech scorer file (.scorer)")
    args = parser.parse_args()
    
    paths = get_project_paths()
    
    # Set default model paths if not specified
    if args.speech and not args.stt_model:
        args.stt_model = os.path.join(paths["models"], "deepspeech-0.9.3-models.pbmm")
    if args.speech and not args.stt_scorer:
        args.stt_scorer = os.path.join(paths["models"], "deepspeech-0.9.3-models.scorer")
        
    # Setup speech components if enabled
    tts_handler, stt_handler = setup_speech_components(
        args.speech, 
        args.tts_engine, 
        args.stt_model, 
        args.stt_scorer
    )
    
    try:
        # File paths
        json_output_path = os.path.join(paths["samples"], "form_structure.json")
        filled_form_path = os.path.join(paths["samples"], "filled_form.json")
        
        # Step 1: Display welcome message
        welcome_message = "[bold cyan]Medical Form Assistant[/bold cyan]\nThis bot will help you complete a medical form.\nI'll guide you through each field with explanations.\nLet's get started!"
        console.print(Panel(welcome_message, title="Welcome", border_style="cyan"))
        
        if tts_handler:
            tts_handler.speak("Medical Form Assistant. This bot will help you complete a medical form. I'll guide you through each field with explanations. Let's get started!")
        
        # Step 2: Use local HTML form
        console.print(Panel("[bold]Using Local HTML Form[/bold]", border_style="blue"))
        sample_form_path = os.path.join(paths["samples"], "medical_form_standard.html")
        
        # Read HTML form
        console.print("[bold]Reading HTML Form...[/bold]")
        html_content = read_html_file(sample_form_path)
        if not html_content:
            return
            
        # Convert HTML to JSON
        console.print("[bold]Converting HTML to JSON...[/bold]")
        form_json = convert_html_to_json(html_content)
        if not form_json:
            console.print(Panel("[red]Conversion failed: Empty JSON output[/red]", border_style="red"))
            return
            
        # Enhance form with metadata
        form_json = enhance_form_schema(form_json)
        save_json_to_file(form_json, json_output_path)
        
        # Step 3: Generate or load form context
        console.print(Panel("[bold]Loading Form Context[/bold]", border_style="blue"))
        form_context = read_latest_summary(paths["summaries"])
        
        if not form_context:
            console.print("[yellow]No existing summary found. Generating new context...[/yellow]")
            form_context = generate_context_for_chatbot()
            
        if form_context:
            console.print("[green]Form context loaded successfully.[/green]")
        else:
            console.print("[yellow]Warning: No form context available. Proceeding without context.[/yellow]")
            
        # Step 4: Initialize components
        console.print(Panel("[bold]Initializing Components[/bold]", border_style="blue"))
        history_manager = ChatHistoryManager(history_file=paths["history"])
        
        model_type = os.getenv("MODEL_TYPE", "ollama").lower()
        if model_type not in ["ollama", "huggingface"]:
            raise ValueError(f"Invalid MODEL_TYPE: {model_type}. Choose 'ollama' or 'huggingface'")
            
        llm_handler = LLMHandler(
            model_type=model_type,
            history_manager=history_manager,
            model_name=os.getenv("MODEL_NAME")
        )
        
        # Step 5: Initialize the form processor with context
        form_processor = FormProcessor(llm_handler, form_context)
        form_processor.load_form(form_json)
        
        # Step 6: Process form with iterative user interaction
        console.print(Panel("[bold]Processing Form with Interactive Communication[/bold]", border_style="blue"))
        
        if args.speech and tts_handler and stt_handler:
            filled_form = process_form_with_speech(form_processor, tts_handler, stt_handler)
        else:
            filled_form = form_processor.process_form()
            
        # Step 7: Summarize collected information
        summary_message = "[bold green]Form Completion Summary[/bold green]\nThank you for completing the medical form. Here's a summary of the information provided:"
        console.print(Panel(summary_message, border_style="green"))
        
        if tts_handler:
            tts_handler.speak("Form Completion Summary. Thank you for completing the medical form. Here's a summary of the information provided:")
            
        summary_text = ""
        for field_name, field_data in filled_form.items():
            if not field_name.startswith('_') and not field_data.get('hidden', False):
                display_name = field_data.get('label', " ".join(word.capitalize() for word in field_name.split('_')))
                value = field_data.get('value', 'Not provided')
                needs_review = field_data.get('needs_review', False)
                review_status = " [NEEDS REVIEW]" if needs_review else ""
                
                field_summary = f"- {display_name}: {value}{review_status}"
                console.print(f"- [bold]{display_name}[/bold]: {value}{review_status}")
                summary_text += field_summary + "\n"
                
        if tts_handler and summary_text:
            tts_handler.speak(summary_text)
            
        # Step 8: Save results
        console.print(Panel("[bold]Saving Results...[/bold]", border_style="blue"))
        save_json_to_file(filled_form, filled_form_path)
        
        # Step 9: Convert JSON to HTML
        console.print(Panel("[bold]Converting JSON to HTML...[/bold]", border_style="blue"))
        html_output_path = os.path.join(paths["samples"], "filled_form.html")
        html_content = convert_json_to_html(filled_form)
        
        if not html_content:
            console.print(Panel("[red]Conversion failed: Empty HTML output[/red]", border_style="red"))
            return
            
        with open(html_output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        completion_message = f"[bold green]Operation completed successfully![/bold green]\nFilled form saved to: [cyan]{filled_form_path}[/cyan]\nHTML version saved to: [cyan]{html_output_path}[/cyan]"
        console.print(Panel(completion_message, border_style="green"))
        
        if tts_handler:
            tts_handler.speak("Operation completed successfully! The filled form has been saved.")
            
        # Report any fields that need review
        review_fields = [k for k, v in filled_form.items() if v.get('needs_review', False)]
        if review_fields:
            console.print(Panel("[yellow]Fields Needing Human Review:[/yellow]", border_style="yellow"))
            review_message = "The following fields need human review:\n"
            
            for field in review_fields:
                display_name = filled_form[field].get('label', field)
                review_reason = filled_form[field].get('review_reason', 'Validation failed')
                
                console.print(f"- [bold]{display_name}[/bold]: {review_reason}")
                review_message += f"- {display_name}: {review_reason}\n"
                
            if tts_handler:
                tts_handler.speak(review_message)
                
        # Clean up resources
        if tts_handler:
            tts_handler.close()
        if stt_handler:
            stt_handler.stop_listening()
                
    except Exception as e:
        console.print(Panel(f"[red]!!! Critical Error: {str(e)}[/red]", title="Critical Error", border_style="red"))
        
        if tts_handler:
            tts_handler.speak(f"Critical Error: {str(e)}")
            tts_handler.close()
            
        if isinstance(e, ImportError):
            console.print("[yellow]Please check your package installations[/yellow]")
        elif "API token" in str(e):
            console.print("[yellow]Verify your .env file contains correct API credentials[/yellow]")
            
if __name__ == "__main__":
    main()
