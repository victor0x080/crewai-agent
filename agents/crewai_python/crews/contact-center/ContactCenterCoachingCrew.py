"""
Contact Center Real-Time Coaching Crew
Provides real-time coaching to contact center representatives during live calls
Manager + 5 specialist coaching agents in hierarchical process

Agents:
- EmpathyCoach: Teaches empathetic language
- PolicyCoach: Ensures policy compliance
- UpsellCoach: Guides appropriate upsells
- NewHireCoach: Provides structured guidance for new reps
- DeEscalationCoach: Helps de-escalate tense conversations
"""

from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from CrewAIManagerService import (
    CrewAIManagerService,
    ManagerConfig,
    redis_client
    # Tools removed - manager agents in hierarchical process should not have tools
)
from crewai import Agent, Task, Crew, Process


# ============================================================================
# COACHING WORKER AGENTS
# ============================================================================

def build_empathy_coach() -> Agent:
    """EmpathyCoach - Teaches empathetic language while keeping handle time low"""
    return Agent(
        role="Empathy & Emotional Intelligence Coach",
        goal="Help representatives respond with appropriate empathy when customers express frustration",
        backstory="""You are EmpathyCoach, a real-time micro-coach for call center representatives.
        You specialize in teaching empathetic language while keeping handle time low.
        
        When a customer expresses frustration and the rep fails to acknowledge it:
        
        Your coaching approach:
        1. In one short sentence, explain what went wrong (e.g., "Customer expressed frustration but wasn't acknowledged")
        2. Provide 1-2 concrete example lines the rep can say RIGHT NOW to recover
        3. Keep it under 350 characters so it fits in a small on-screen card
        4. Be supportive, never scolding
        5. Optionally suggest a 30-second micro-exercise for after the call
        
        Tailor your response based on:
        - Rep's tenure (novice needs more structure)
        - Rep's avg_csat score (lower scores need more empathy focus)
        - Rep's top training needs
        - Customer sentiment (angry customers need more acknowledgment)
        
        Example frustration phrases to watch for:
        - "This is ridiculous"
        - "I'm very upset"
        - "This is frustrating"
        - "Unacceptable"
        - "This ruined my trip"
        
        Example empathy responses to suggest:
        - "I'm so sorry this happened"
        - "I totally understand how frustrating this must be"
        - "I apologize for this inconvenience"
        - "I understand this has been stressful"
        
        Your tone is always warm, supportive, and practical.""",
        allow_delegation=False,
        verbose=True
    )


def build_policy_coach() -> Agent:
    """PolicyCoach - Ensures policy compliance while delighting customers"""
    return Agent(
        role="Policy & Compliance Coach",
        goal="Help reps follow company policy while still providing excellent customer service",
        backstory="""You are PolicyCoach, a real-time compliance guide for contact center representatives.
        Your goal is to help reps follow policy while still delighting the customer.
        
        Common policy violations you watch for:
        - Offering refunds/compensation without checking policy first
        - Accessing customer accounts without verification
        - Making unauthorized changes
        - Sharing confidential information
        - Bypassing required approval workflows
        
        Your coaching approach:
        1. In one sentence, explain the policy risk in non-legal terms (e.g., "This refund needs manager approval first")
        2. Provide a replacement script that stays within policy
        3. Add a brief tip tailored to the rep's experience level
        4. Keep it under 400 characters
        5. Never sound bureaucratic - focus on protecting both customer and company
        
        Verification phrases to encourage:
        - "For security, let me verify your account details"
        - "Before I access your booking..."
        - "Can I confirm your last name and reservation date?"
        
        Policy compliance phrases to suggest:
        - "Let me check what I'm authorized to do under our policy"
        - "Our policy allows me to..."
        - "I need to escalate this to my supervisor who can approve..."
        
        Tailor based on:
        - Rep's compliance_score (lower scores get more structure)
        - Rep's tenure (novices need clearer boundaries)
        - Severity of potential violation
        
        Always protect the rep and the company while maintaining customer trust.""",
        allow_delegation=False,
        verbose=True
    )


def build_upsell_coach() -> Agent:
    """UpsellCoach - Guides appropriate, value-adding upsells"""
    return Agent(
        role="Consultative Upselling Coach",
        goal="Help reps spot and execute appropriate upsell opportunities without sounding pushy",
        backstory="""You are UpsellCoach, a real-time micro-coach for ethical, customer-centric upselling.
        Your mission is to help reps offer relevant upsells that add value without being pushy or extending handle time.
        
        You watch for missed opportunities:
        - Customer mentions future travel → Suggest loyalty program
        - Business traveler → Highlight business benefits
        - VIP customer → Premium service upgrades
        - Resolved issue → Preventive features/services
        - Multiple bookings → Package deals
        
        Your coaching approach:
        1. In one sentence, explain what upsell opportunity is available right now
        2. Provide 1-2 concise example lines the rep can say immediately
        3. Frame as consultative, not salesy
        4. If rep has low upsell_rate or is novice, add a tip on timing and phrasing
        5. Keep under 400 characters
        
        Examples of consultative upsell language:
        - "Since you travel often, you might benefit from..."
        - "Many business travelers find this helpful..."
        - "To prevent this in the future, we have..."
        - "Would you like me to note this preference for next time?"
        
        Tailor based on:
        - Rep's upsell_rate (low rates need encouragement)
        - Rep's tenure (novices need simpler approaches)
        - Customer segment (business/leisure/VIP)
        - Vertical (hotel/airline/travel)
        
        Key principles:
        - Only suggest if it genuinely helps the customer
        - Never pushy or aggressive
        - Keep it brief and natural
        - Focus on value, not price
        
        You help reps see upselling as problem-solving, not selling.""",
        allow_delegation=False,
        verbose=True
    )


def build_newhire_coach() -> Agent:
    """NewHireCoach - Provides structured guidance for new representatives"""
    return Agent(
        role="New Hire Onboarding Coach",
        goal="Give new reps simple, step-by-step structure during calls",
        backstory="""You are NewHireCoach, a supportive guide for new or less-experienced contact center representatives.
        Your role is to provide simple, structured guidance they can follow during the call.
        
        Focus on basic call flow:
        1. Opening (greeting + warmth)
        2. Verification (security before access)
        3. Discovery (understand the issue)
        4. Resolution (solve or escalate)
        5. Reassurance (set expectations)
        6. Closing (thank + invite back)
        
        Common mistakes you watch for:
        - Skipped verification steps
        - Missing required scripts
        - Not setting expectations
        - Abrupt endings
        - No discovery questions
        
        Your coaching approach:
        1. In one sentence, explain what step they skipped (e.g., "You skipped identity verification")
        2. Provide a clear, ready-to-read script (1-2 lines) to fix it RIGHT NOW
        3. Add a mini checklist of at most 3 bullet points for this call phase
        4. Keep under 450 characters
        5. Always encouraging, never blaming
        
        Example checklists:
        - Opening: "1) Greet warmly, 2) Verify identity, 3) Express willingness to help"
        - Resolution: "1) Explain solution, 2) Confirm understanding, 3) Set timeline"
        - Closing: "1) Summarize action, 2) Thank customer, 3) Invite future contact"
        
        Tailor based on:
        - Rep tenure (< 6 months = novice)
        - Rep skill_level
        - Top training needs
        
        Your tone is patient, clear, and confidence-building.
        You treat every mistake as a learning opportunity.""",
        allow_delegation=False,
        verbose=True
    )


def build_deescalation_coach() -> Agent:
    """DeEscalationCoach - Guides tense conversation de-escalation"""
    return Agent(
        role="De-Escalation & Conflict Resolution Coach",
        goal="Help reps de-escalate angry or emotional customers while protecting the rep",
        backstory="""You are DeEscalationCoach, a real-time assistant for managing difficult conversations.
        Your job is to lower the temperature while keeping within policy and supporting the rep.
        
        Escalation warning signs:
        - Raised voice or shouting language
        - Threats ("I'll cancel everything")
        - Personal attacks
        - Repeated frustration with no acknowledgment
        - Demands that violate policy
        
        Your coaching approach:
        1. In one calm sentence, name what's happening emotionally (e.g., "Customer is very frustrated and needs to feel heard")
        2. Provide 1-2 de-escalation lines combining empathy + control of next steps
        3. Give one quick self-coaching tip (e.g., "slow your pace," "pause before replying")
        4. Keep under 400 characters
        5. Be on the rep's side - protect their well-being
        
        De-escalation techniques:
        - Acknowledge emotion first: "I hear how frustrated you are"
        - Take ownership: "Let me make this right"
        - Provide control: "Here's what I can do right now..."
        - Slow the pace: Speak calmly and deliberately
        - Set boundaries: "I want to help you, and I need..."
        
        Example de-escalation scripts:
        - "I completely understand why you're upset. Let me see what I can do right now."
        - "I hear you, and I want to make this right. Here's what I'm going to do..."
        - "This clearly hasn't met your expectations. Let me fix this for you."
        
        Self-coaching tips:
        - "Take a breath before responding"
        - "Lower your pace and tone"
        - "Stay calm, you're doing great"
        - "Focus on what you CAN do"
        
        Tailor based on:
        - Customer sentiment_tendency (angry needs more acknowledgment)
        - Rep's avg_csat (lower scores need more support)
        - Rep's training needs (empathy deficits need more scripts)
        
        If customer becomes abusive, remind rep:
        - "If this continues, you can escalate to supervisor"
        - "Protect yourself - you don't have to tolerate abuse"
        
        Your role is to support the rep emotionally while giving practical tools.""",
        allow_delegation=False,
        verbose=True
    )


# ============================================================================
# MANAGER AGENT
# ============================================================================

def build_coaching_manager() -> Agent:
    """Coaching Manager - Not used in specialist routing mode"""
    return Agent(
        role="Real-Time Coaching Coordinator",
        goal="Route to specialists",
        backstory="""Routing coordinator.""",
        tools=[],
        allow_delegation=False,
        verbose=True
    )


# ============================================================================
# SPECIALIST COACHING TASKS
# ============================================================================

def build_empathy_coaching_task(empathy_coach: Agent) -> Task:
    """Task for Empathy Coach"""
    return Task(
        description="""Create a 350-450 character supportive coaching tip with 1-2 scripts for a no_empathy issue.

        Input variables available:
        - source_event: Contains data.transcript_snippet, data.rep_profile, data.customer_profile, data.severity
        - actual_issue_type: The issue type (no_empathy)
        
        Access the data:
        - transcript_snippet: {source_event[data][transcript_snippet]}
        - rep_profile: {source_event[data][rep_profile]}
        - customer_profile: {source_event[data][customer_profile]}
        - severity: {source_event[data][severity]}
        
        Generate a JSON response with:
        {
            "agent_name": "Empathy & Emotional Intelligence Coach",
            "title": "<brief title>",
            "message": "<coaching message (350-450 chars)>",
            "suggested_responses": ["<script1>", "<script2>"],
            "micro_exercise": "<optional 30-second exercise>"
        }
        
        Your coaching should:
        - Acknowledge the customer's frustration that was missed
        - Provide 1-2 empathetic response scripts the rep can use RIGHT NOW
        - Keep under 350 characters
        - Be warm, supportive, and practical
        - Tailor based on rep's tenure, avg_csat, and customer sentiment""",
        agent=empathy_coach,
        expected_output="JSON object with agent_name, title, message, suggested_responses, and micro_exercise"
    )


def build_policy_coaching_task(policy_coach: Agent) -> Task:
    """Task for Policy & Compliance Coach"""
    return Task(
        description="""Create a 350-450 character supportive coaching tip with 1-2 scripts for a missing_verification or policy_violation issue.

        Input variables available:
        - source_event: Contains data.transcript_snippet, data.rep_profile, data.customer_profile, data.severity
        - actual_issue_type: The issue type (missing_verification or policy_violation)
        
        Access the data:
        - transcript_snippet: {source_event[data][transcript_snippet]}
        - rep_profile: {source_event[data][rep_profile]}
        - customer_profile: {source_event[data][customer_profile]}
        - severity: {source_event[data][severity]}
        
        Generate a JSON response with:
        {
            "agent_name": "Policy & Compliance Coach",
            "title": "<brief title>",
            "message": "<coaching message (350-450 chars)>",
            "suggested_responses": ["<script1>", "<script2>"],
            "micro_exercise": "<optional 30-second exercise>"
        }
        
        Your coaching should:
        - Explain the policy risk in simple, non-legal terms
        - Provide replacement script that stays within policy
        - Keep under 400 characters
        - Focus on protecting both customer and company
        - Never sound bureaucratic""",
        agent=policy_coach,
        expected_output="JSON object with agent_name, title, message, suggested_responses, and micro_exercise"
    )


def build_upsell_coaching_task(upsell_coach: Agent) -> Task:
    """Task for Upsell Coach"""
    return Task(
        description="""Create a 350-450 character supportive coaching tip with 1-2 scripts for a missed_upsell opportunity.

        Input variables available:
        - source_event: Contains data.transcript_snippet, data.rep_profile, data.customer_profile, data.severity
        - actual_issue_type: The issue type (missed_upsell)
        
        Access the data:
        - transcript_snippet: {source_event[data][transcript_snippet]}
        - rep_profile: {source_event[data][rep_profile]}
        - customer_profile: {source_event[data][customer_profile]}
        - severity: {source_event[data][severity]}
        
        Generate a JSON response with:
        {
            "agent_name": "Consultative Upselling Coach",
            "title": "<brief title>",
            "message": "<coaching message (350-450 chars)>",
            "suggested_responses": ["<script1>", "<script2>"],
            "micro_exercise": "<optional 30-second exercise>"
        }
        
        Your coaching should:
        - Identify the upsell opportunity that was missed
        - Provide 1-2 consultative upsell scripts (not pushy)
        - Keep under 400 characters
        - Frame as value-adding, not salesy
        - Focus on helping the customer, not selling""",
        agent=upsell_coach,
        expected_output="JSON object with agent_name, title, message, suggested_responses, and micro_exercise"
    )


def build_newhire_coaching_task(newhire_coach: Agent) -> Task:
    """Task for New Hire Coach"""
    return Task(
        description="""Create a 350-450 character supportive coaching tip with 1-2 scripts for a script_noncompliance issue or new rep guidance.

        Input variables available:
        - source_event: Contains data.transcript_snippet, data.rep_profile, data.customer_profile, data.severity
        - actual_issue_type: The issue type (script_noncompliance)
        
        Access the data:
        - transcript_snippet: {source_event[data][transcript_snippet]}
        - rep_profile: {source_event[data][rep_profile]}
        - customer_profile: {source_event[data][customer_profile]}
        - severity: {source_event[data][severity]}
        
        Generate a JSON response with:
        {
            "agent_name": "New Hire Onboarding Coach",
            "title": "<brief title>",
            "message": "<coaching message (350-450 chars)>",
            "suggested_responses": ["<script1>", "<script2>"],
            "micro_exercise": "<optional 30-second exercise>"
        }
        
        Your coaching should:
        - Explain what step was skipped in simple terms
        - Provide clear, ready-to-use script (1-2 lines) to fix it RIGHT NOW
        - Add mini checklist of at most 3 bullet points for this call phase
        - Keep under 450 characters
        - Be patient, clear, and confidence-building
        - Never blame - treat mistakes as learning opportunities""",
        input_variables=["source_event", "actual_issue_type"],
        agent=newhire_coach,
        expected_output="JSON object with agent_name, title, message, suggested_responses, and micro_exercise"
    )


def build_deescalation_coaching_task(deescalation_coach: Agent) -> Task:
    """Task for De-Escalation Coach"""
    return Task(
        description="""Create a 350-450 character supportive coaching tip with 1-2 scripts for an escalation_risk issue or angry customer.

        Input variables available:
        - source_event: Contains data.transcript_snippet, data.rep_profile, data.customer_profile, data.severity
        - actual_issue_type: The issue type (escalation_risk)
        
        Access the data:
        - transcript_snippet: {source_event[data][transcript_snippet]}
        - rep_profile: {source_event[data][rep_profile]}
        - customer_profile: {source_event[data][customer_profile]}
        - severity: {source_event[data][severity]}
        
        Generate a JSON response with:
        {
            "agent_name": "De-Escalation & Conflict Resolution Coach",
            "title": "<brief title>",
            "message": "<coaching message (350-450 chars)>",
            "suggested_responses": ["<script1>", "<script2>"],
            "micro_exercise": "<optional 30-second exercise>"
        }
        
        Your coaching should:
        - Name what's happening emotionally (e.g., "Customer is very frustrated and needs to feel heard")
        - Provide 1-2 de-escalation scripts combining empathy + control of next steps
        - Add one quick self-coaching tip (e.g., "slow your pace", "pause before replying")
        - Keep under 400 characters
        - Be on the rep's side - protect their well-being
        - Support the rep emotionally while giving practical tools""",
        agent=deescalation_coach,
        expected_output="JSON object with agent_name, title, message, suggested_responses, and micro_exercise"
    )


# ============================================================================
# MAIN TASK
# ============================================================================

def build_main_task(manager: Agent) -> Task:
    """Main task - not used in specialist routing mode"""
    return Task(
        description="""Placeholder task.""",
        agent=manager,
        expected_output="""Placeholder."""
    )


def get_specialist_for_issue_type(issue_type: str, coaches: list, coaching_tasks: list) -> tuple:
    """Get the appropriate specialist agent and task for an issue type"""
    issue_type_map = {
        'no_empathy': 0,  # Empathy coach
        'missing_verification': 1,  # Policy coach
        'policy_violation': 1,  # Policy coach
        'missed_upsell': 2,  # Upsell coach
        'script_noncompliance': 3,  # New hire coach
        'escalation_risk': 4  # De-escalation coach
    }
    
    idx = issue_type_map.get(issue_type, 0)  # Default to empathy coach
    return coaches[idx], coaching_tasks[idx]


# ============================================================================
# BUILD CREW
# ============================================================================

def build_crew() -> tuple[ManagerConfig, Crew]:
    """Build the Contact Center Coaching Crew"""
    
    # Config
    config = ManagerConfig(
        manager_id="coaching-manager",
        crew_id="contact-center-coaching-crew",
        route_stream="stream:contact_center:issues",
        consumer_group="coaching",
        consumer_name="coaching-1"
    )
    
    # Build manager
    manager = build_coaching_manager()
    
    # Build specialist coaches
    empathy_coach = build_empathy_coach()
    policy_coach = build_policy_coach()
    upsell_coach = build_upsell_coach()
    newhire_coach = build_newhire_coach()
    deescalation_coach = build_deescalation_coach()
    
    coaches = [empathy_coach, policy_coach, upsell_coach, newhire_coach, deescalation_coach]
    
    # Build specialist coaching tasks (each assigned to a specific coach)
    coaching_tasks = [
        build_empathy_coaching_task(empathy_coach),
        build_policy_coaching_task(policy_coach),
        build_upsell_coaching_task(upsell_coach),
        build_newhire_coaching_task(newhire_coach),
        build_deescalation_coaching_task(deescalation_coach)
    ]
    
    # Build main routing task
    main_task = build_main_task(manager)
    
    # Store specialists for dynamic routing
    # The CrewAIManagerService will build crews dynamically based on issue_type
    config.specialists = {
        'coaches': coaches,
        'tasks': coaching_tasks
    }
    
    # Build a default crew (will be replaced dynamically per issue)
    # Using empathy coach as default
    crew = Crew(
        agents=[empathy_coach],
        tasks=[coaching_tasks[0]],
        process=Process.sequential,
        verbose=True
    )
    
    # Verify crew setup and agent visibility
    print(f"\n[Crew Setup] Manager: {manager.role}")
    print(f"[Crew Setup] Manager can delegate: {manager.allow_delegation}")
    print(f"[Crew Setup] Workers ({len(coaches)}):")
    for i, coach in enumerate(coaches, 1):
        print(f"  {i}. {coach.role} (can delegate: {coach.allow_delegation})")
    print(f"[Crew Setup] Process: {crew.process}")
    print(f"[Crew Setup] Total agents in crew: {len(crew.agents)}")
    print(f"[Crew Setup] Manager agent set: {crew.manager_agent is not None}")
    
    # Verify manager can see worker agents (for debugging)
    if hasattr(crew, 'agents') and crew.agents:
        print(f"[Crew Setup] Worker agent roles available for delegation:")
        for agent in crew.agents:
            print(f"  - {agent.role}")
    
    return config, crew


# ============================================================================
# REGISTRATION
# ============================================================================

def register_crew():
    """Show registration command"""
    print("""
To register this crew, run:

curl -X POST http://localhost:3001/api/managers/register \\
  -H "Content-Type: application/json" \\
  -d '{
    "manager_id": "coaching-manager",
    "crew_id": "contact-center-coaching-crew",
    "route_stream": "stream:route.decisions:coaching-manager",
    "consumes_types": [
      "contact_center.issue.detected"
    ],
    "produces_streams": [
      "stream:coaching:messages"
    ],
    "produces_schemas": [
      "CoachingMessageV1"
    ],
    "capabilities": [
      "real_time_coaching",
      "empathy_training",
      "policy_compliance",
      "upsell_guidance",
      "new_hire_support",
      "de_escalation"
    ],
    "policy": {
      "min_confidence": 0.7,
      "max_latency_ms": 5000,
      "max_error_rate_pct": 5,
      "failure_threshold": 3,
      "success_threshold": 2,
      "timeout_ms": 10000
    },
    "owner": "contact-center-ops@acme",
    "description": "Real-time coaching crew for contact center representatives with 5 specialist coaches"
  }'
    """)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    print("=== Contact Center Real-Time Coaching Crew ===\n")
    
    # Build crew
    config, crew = build_crew()
    
    print(f"Manager: {crew.manager_agent.role}")
    print(f"Coaches: {len(crew.agents)}")
    print(f"Process: {crew.process}")
    print(f"\nCoaching Specialists:")
    for i, agent in enumerate(crew.agents, 1):
        print(f"  {i}. {agent.role}")
    
    # Show registration command
    print("\n")
    register_crew()
    
    # Start service
    print(f"\nStarting Coaching Manager Service...")
    print(f"Route stream: {config.route_stream}\n")
    
    service = CrewAIManagerService(config, crew.manager_agent, crew)
    
    try:
        service.start()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        service.stop()

