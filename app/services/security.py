"""
Security service implementing CrowdStrike AIDR SDK integration.

This module follows the exact AIDR SDK pattern for scanning
all AI interactions (input and output) through CrowdStrike AI Guard.

SDK Pattern:
    from crowdstrike_aidr import AIGuard
    from crowdstrike_aidr.models.ai_guard import ExtraInfo
    
    client = AIGuard(
        base_url_template="https://api.crowdstrike.com/aidr/aiguard",
        token="<AIDR_TOKEN>",
    )
    
    response = client.guard_chat_completions(
        guard_input={"messages": [{"role": "user", "content": "..."}]},
        event_type="input",  # or "output"
        app_id="AegisAI",
        user_id="user_id",
        llm_provider="OpenAI",
        model="GPT-5",
        model_version="latest",
        source_ip="127.0.0.1",
        extra_info=ExtraInfo(user_name="user@example.com", app_name="AegisAI")
    )
"""

import os
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum

import httpx

from app.core.config import load_config


class EventType(str, Enum):
    """Event types for AIDR scanning."""
    INPUT = "input"
    OUTPUT = "output"


@dataclass
class ExtraInfo:
    """
    Extra information for AIDR guard requests.
    Matches the crowdstrike_aidr.models.ai_guard.ExtraInfo structure.
    """
    user_name: str  # Mandatory: The user's email
    app_name: str = "AegisAI"


@dataclass
class GuardResponse:
    """
    Response from AIDR guard request.
    
    AIDR Response Processing Logic:
    
    1. Check access_rules first - if matched=true and action=blocked, deny access entirely
    2. Check result.blocked - if true, block the content with summary message
    3. Check result.guard_output.messages - if present, use transformed content
    
    Response structure:
    {
        "request_id": "...",
        "status": "Success",
        "summary": "Description of what happened",
        "result": {
            "blocked": true/false,
            "transformed": true/false,
            "guard_output": {
                "messages": [{"role": "user", "content": "transformed content"}]
            },
            "access_rules": {
                "rule_name": {
                    "matched": true/false,
                    "action": "blocked/reported",
                    "name": "Human readable name"
                }
            },
            "detectors": {...}
        }
    }
    """
    allowed: bool                          # Whether the request should proceed
    access_denied: bool                    # True if access_rules blocked the user entirely
    content_blocked: bool                  # True if content was blocked (but user has access)
    transformed: bool                      # True if content was transformed/redacted
    transformed_content: Optional[str]     # The transformed content to use instead of original
    summary: str                           # Summary message from AIDR
    error_message: str                     # User-facing error message
    raw_response: Optional[Dict[str, Any]] = None


def _to_dict(obj: Any) -> Dict[str, Any]:
    """Convert an object to a dictionary."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, 'model_dump'):
        return obj.model_dump()
    if hasattr(obj, 'dict'):
        return obj.dict()
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    return {}


def _aidr_request_raw(
    base_url: str,
    token: str,
    guard_input: Dict[str, Any],
    event_type: str,
    app_id: str,
    user_id: str,
    llm_provider: str,
    model: str,
    model_version: str,
    source_ip: str,
    extra_info: ExtraInfo,
) -> Optional[Dict[str, Any]]:
    """
    Call AIDR API directly via HTTP when the SDK fails (e.g. ValidationError
    due to extra fields like access_rules.*.detected). Returns raw JSON dict
    or None on failure.
    """
    if not token or not base_url:
        return None
    url = base_url.rstrip("/") + "/v1/guard_chat_completions"
    body = {
        "guard_input": guard_input,
        "app_id": app_id,
        "event_type": event_type,
        "extra_info": {"user_name": extra_info.user_name, "app_name": extra_info.app_name},
        "llm_provider": llm_provider,
        "model": model,
        "model_version": model_version,
        "source_ip": source_ip,
        "user_id": user_id,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        print(f"AIDR raw HTTP fallback error: {e}")
        return None


def _parse_sdk_response(response: Any) -> GuardResponse:
    """
    Parse the CrowdStrike AIDR SDK response.
    
    Processing order:
    1. Check access_rules - if any rule has matched=true AND action=blocked, deny access
    2. Check result.blocked - if true, block content and return summary
    3. Check result.guard_output.messages - if present, extract transformed content
    
    Args:
        response: The raw SDK response object
        
    Returns:
        GuardResponse with parsed data
    """
    try:
        # Convert response to dict
        raw_dict = _to_dict(response)
        
        # Get top-level fields
        summary = raw_dict.get('summary', '')
        result = raw_dict.get('result', {})
        if not isinstance(result, dict):
            result = _to_dict(result)
        
        # ========================================
        # Step 1: Check access_rules FIRST
        # If matched=true AND action=blocked, user is denied access entirely
        # ========================================
        access_rules = result.get('access_rules', {})
        if not isinstance(access_rules, dict):
            access_rules = _to_dict(access_rules)
        
        for rule_key, rule_data in access_rules.items():
            if not isinstance(rule_data, dict):
                rule_data = _to_dict(rule_data)
            
            matched = rule_data.get('matched', False)
            action = rule_data.get('action', '').lower()
            rule_name = rule_data.get('name', rule_key)
            
            if matched and action == 'blocked':
                print(f"AIDR: Access DENIED - Rule '{rule_name}' blocked user")
                access_error_msg = f"**Prompt Blocked!**\nThis interaction was flagged and blocked by the security layer.\nIdentification: {rule_name}"
                return GuardResponse(
                    allowed=False,
                    access_denied=True,
                    content_blocked=False,
                    transformed=False,
                    transformed_content=None,
                    summary=summary,
                    error_message=access_error_msg,
                    raw_response=raw_dict
                )
        
        # ========================================
        # Step 2: Check if content is blocked
        # result.blocked = true means content was blocked
        # ========================================
        is_blocked = result.get('blocked', False)
        
        if is_blocked:
            # Content is blocked - return the summary as error message
            error_msg = summary if summary else "Content blocked by security policy."
            print(f"AIDR: Content BLOCKED - {error_msg}")
            return GuardResponse(
                allowed=False,
                access_denied=False,
                content_blocked=True,
                transformed=False,
                transformed_content=None,
                summary=summary,
                error_message=error_msg,
                raw_response=raw_dict
            )
        
        # ========================================
        # Step 3: Check for transformed content
        # If guard_output.messages exists, use that content instead
        # ========================================
        is_transformed = result.get('transformed', False)
        transformed_content = None
        
        guard_output = result.get('guard_output', {})
        if not isinstance(guard_output, dict):
            guard_output = _to_dict(guard_output)
        
        messages = guard_output.get('messages', [])
        if messages and isinstance(messages, list):
            # Extract all content from messages and combine
            content_parts = []
            for msg in messages:
                if isinstance(msg, dict):
                    content = msg.get('content', '')
                else:
                    msg_dict = _to_dict(msg)
                    content = msg_dict.get('content', '')
                if content:
                    content_parts.append(content)
            
            if content_parts:
                transformed_content = '\n'.join(content_parts)
                is_transformed = True
                print(f"AIDR: Content TRANSFORMED - Using redacted/modified content")
        
        # ========================================
        # Step 4: Content is allowed (possibly transformed)
        # ========================================
        print(f"AIDR: Request ALLOWED - Transformed: {is_transformed}")
        
        return GuardResponse(
            allowed=True,
            access_denied=False,
            content_blocked=False,
            transformed=is_transformed,
            transformed_content=transformed_content,
            summary=summary,
            error_message="",
            raw_response=raw_dict
        )
        
    except Exception as e:
        print(f"Error parsing AIDR response: {e}")
        import traceback
        traceback.print_exc()
        # Return a safe default on parse error - allow to prevent blocking on errors
        return GuardResponse(
            allowed=True,
            access_denied=False,
            content_blocked=False,
            transformed=False,
            transformed_content=None,
            summary="",
            error_message="",
            raw_response=None
        )


class AIGuardClient:
    """
    CrowdStrike AI Guard client for scanning AI interactions.
    
    Implements the exact SDK pattern:
    - Initialization with base_url_template and token
    - guard_chat_completions method with required parameters
    """
    
    def __init__(
        self,
        base_url_template: Optional[str] = None,
        token: Optional[str] = None
    ):
        """
        Initialize the AI Guard client.
        
        Args:
            base_url_template: The AIDR API URL (defaults to config AIDR_URL)
            token: The AIDR API token (defaults to config AIDR_TOKEN)
        """
        config = load_config()
        self.base_url = base_url_template or config.get("AIDR_URL", "https://api.crowdstrike.com/aidr/aiguard")
        self.token = token or config.get("AIDR_TOKEN", "")
        self._client = None
        self._sdk_available = False
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the underlying AIDR SDK client."""
        if not self.token:
            print("AIDR: No token configured, using fallback mode")
            return
            
        try:
            from crowdstrike_aidr import AIGuard
            self._client = AIGuard(
                base_url_template=self.base_url,
                token=self.token
            )
            self._sdk_available = True
            print("AIDR: SDK initialized successfully")
        except ImportError:
            print("AIDR: SDK not installed, using fallback mode")
            self._client = None
        except Exception as e:
            print(f"AIDR: SDK initialization error: {e}")
            self._client = None
    
    def guard_chat_completions(
        self,
        guard_input: Dict[str, Any],
        event_type: str,
        app_id: str,
        user_id: str,
        llm_provider: str,
        model: str,
        model_version: str,
        source_ip: str,
        extra_info: ExtraInfo
    ) -> GuardResponse:
        """
        Guard a chat completion request through AIDR.
        
        This method follows the exact SDK pattern:
        - guard_input: {"messages": [{"role": "user", "content": "..."}]}
        - event_type: "input" or "output"
        - extra_info: ExtraInfo with user_name (email) and app_name
        
        Args:
            guard_input: The input to scan (messages format)
            event_type: "input" for user prompts, "output" for LLM responses
            app_id: Application identifier (always "AegisAI")
            user_id: User ID from database
            llm_provider: Provider name (e.g., "Anthropic", "OpenAI")
            model: Model name (e.g., "GPT-5")
            model_version: Model version (default "latest")
            source_ip: Client IP address
            extra_info: ExtraInfo object with user_name and app_name
            
        Returns:
            GuardResponse with scan results
        """
        if self._client is not None and self._sdk_available:
            # Use actual SDK
            try:
                from crowdstrike_aidr.models.ai_guard import ExtraInfo as SDKExtraInfo
                
                sdk_extra_info = SDKExtraInfo(
                    user_name=extra_info.user_name,
                    app_name=extra_info.app_name
                )
                
                response = self._client.guard_chat_completions(
                    guard_input=guard_input,
                    event_type=event_type,
                    app_id=app_id,
                    user_id=user_id,
                    llm_provider=llm_provider,
                    model=model,
                    model_version=model_version,
                    source_ip=source_ip,
                    extra_info=sdk_extra_info
                )
                
                # Parse the SDK response properly
                return _parse_sdk_response(response)
                
            except Exception as e:
                # Log error (e.g. ValidationError when API returns extra fields like access_rules.*.detected)
                print(f"AIDR SDK error: {e}")
                # Raw HTTP fallback: call AIDR API directly and parse response (tolerates extra fields)
                raw = _aidr_request_raw(
                    self.base_url,
                    self.token,
                    guard_input,
                    event_type,
                    app_id,
                    user_id,
                    llm_provider,
                    model,
                    model_version,
                    source_ip,
                    extra_info,
                )
                if raw is not None:
                    print("AIDR: Using raw HTTP response (SDK validation bypass)")
                    return _parse_sdk_response(raw)
                # No raw response - allow on error to prevent blocking
                return GuardResponse(
                    allowed=True,
                    access_denied=False,
                    content_blocked=False,
                    transformed=False,
                    transformed_content=None,
                    summary=f"AIDR SDK validation error: {e}",
                    error_message="",
                    raw_response=None
                )
        else:
            # Fallback when SDK not available (for testing/development)
            return GuardResponse(
                allowed=True,
                access_denied=False,
                content_blocked=False,
                transformed=False,
                transformed_content=None,
                summary="",
                error_message="",
                raw_response=None
            )


class SecurityService:
    """
    High-level security service for Aegis AI.
    
    Provides methods for scanning user inputs and LLM outputs
    through CrowdStrike AIDR.
    """
    
    def __init__(self, client: Optional[AIGuardClient] = None):
        """
        Initialize the security service.
        
        Args:
            client: Optional AIGuardClient instance (for dependency injection/testing)
        """
        self.client = client or AIGuardClient()
    
    def scan_input(
        self,
        content: str,
        user_id: str,
        user_email: str,
        llm_provider: str,
        model: str,
        source_ip: str = "127.0.0.1",
        model_version: str = "latest",
        app_name: str = "AegisAI"
    ) -> GuardResponse:
        """
        Scan user input before sending to LLM.
        
        Args:
            content: The user's message/prompt
            user_id: User ID from database
            user_email: User's email address (for ExtraInfo.user_name)
            llm_provider: AI provider (e.g., "OpenAI", "Anthropic")
            model: Model name
            source_ip: Client IP address
            model_version: Model version
            app_name: Application name to send to AIDR
            
        Returns:
            GuardResponse with scan results
        """
        guard_input = {
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ]
        }
        
        extra_info = ExtraInfo(
            user_name=user_email,
            app_name=app_name
        )
        
        return self.client.guard_chat_completions(
            guard_input=guard_input,
            event_type=EventType.INPUT.value,
            app_id=app_name,
            user_id=user_id,
            llm_provider=llm_provider,
            model=model,
            model_version=model_version,
            source_ip=source_ip,
            extra_info=extra_info
        )
    
    def scan_input_context(
        self,
        messages: list,
        user_id: str,
        user_email: str,
        llm_provider: str,
        model: str,
        source_ip: str = "127.0.0.1",
        model_version: str = "latest",
        app_name: str = "AegisAI"
    ) -> GuardResponse:
        """
        Scan multiple messages for context-aware AIDR detection.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            user_id: User ID from database
            user_email: User's email address (for ExtraInfo.user_name)
            llm_provider: AI provider (e.g., "OpenAI", "Anthropic")
            model: Model name
            source_ip: Client IP address
            model_version: Model version
            app_name: Application name to send to AIDR
            
        Returns:
            GuardResponse with scan results
        """
        guard_input = {"messages": messages}
        
        extra_info = ExtraInfo(
            user_name=user_email,
            app_name=app_name
        )
        
        return self.client.guard_chat_completions(
            guard_input=guard_input,
            event_type=EventType.INPUT.value,
            app_id=app_name,
            user_id=user_id,
            llm_provider=llm_provider,
            model=model,
            model_version=model_version,
            source_ip=source_ip,
            extra_info=extra_info
        )
    
    def scan_output(
        self,
        content: str,
        user_id: str,
        user_email: str,
        llm_provider: str,
        model: str,
        source_ip: str = "127.0.0.1",
        model_version: str = "latest",
        app_name: str = "AegisAI"
    ) -> GuardResponse:
        """
        Scan LLM output before returning to user.
        
        Args:
            content: The LLM's response
            user_id: User ID from database
            user_email: User's email address (for ExtraInfo.user_name)
            llm_provider: AI provider (e.g., "OpenAI", "Anthropic")
            model: Model name
            source_ip: Client IP address
            model_version: Model version
            app_name: Application name to send to AIDR
            
        Returns:
            GuardResponse with scan results
        """
        guard_input = {
            "messages": [
                {
                    "role": "assistant",
                    "content": content
                }
            ]
        }
        
        extra_info = ExtraInfo(
            user_name=user_email,
            app_name=app_name
        )
        
        return self.client.guard_chat_completions(
            guard_input=guard_input,
            event_type=EventType.OUTPUT.value,
            app_id=app_name,
            user_id=user_id,
            llm_provider=llm_provider,
            model=model,
            model_version=model_version,
            source_ip=source_ip,
            extra_info=extra_info
        )


# Singleton instance for convenience
_security_service: Optional[SecurityService] = None


def get_security_service() -> SecurityService:
    """Get the global security service instance."""
    global _security_service
    if _security_service is None:
        _security_service = SecurityService()
    return _security_service
