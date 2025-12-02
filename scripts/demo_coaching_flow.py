#!/usr/bin/env python3
"""
Contact Center Coaching - Flow Demonstration
Shows how transcript turns trigger detection → coaching without requiring live services
"""

import sys
from pathlib import Path
from datetime import datetime

# Colors
GREEN = '\033[0;32m'
BLUE = '\033[0;34m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
PURPLE = '\033[0;35m'
CYAN = '\033[0;36m'
NC = '\033[0m'  # No Color

def print_header(text):
    print(f"\n{'='*70}")
    print(f"{CYAN}{text}{NC}")
    print(f"{'='*70}\n")

def print_transcript_turn(turn_num, speaker, text):
    if speaker == "customer":
        icon = f"{GREEN}🧑 CUSTOMER{NC}"
        color = GREEN
    else:
        icon = f"{BLUE}👤 REP{NC}"
        color = BLUE
    
    print(f"{icon}: {color}{text}{NC}")
    print(f"   └─ Turn {turn_num} at {datetime.now().strftime('%H:%M:%S')}")

def print_detection(issue_type, severity, detected_at):
    severity_color = RED if severity == "high" else YELLOW if severity == "medium" else BLUE
    print(f"\n{severity_color}🚨 ISSUE DETECTED{NC}")
    print(f"   Type: {issue_type}")
    print(f"   Severity: {severity_color}{severity.upper()}{NC}")
    print(f"   Detected at turn: {detected_at}")

def print_coaching(agent_name, title, message, scripts, severity):
    severity_color = RED if severity == "high" else YELLOW if severity == "medium" else BLUE
    
    print(f"\n{PURPLE}{'='*70}")
    print(f"🤖 AI COACH: {agent_name}")
    print(f"{'='*70}{NC}")
    print(f"\n{severity_color}▶ {title}{NC}")
    print(f"\n{message}")
    
    if scripts:
        print(f"\n{CYAN}💬 TRY SAYING:{NC}")
        for i, script in enumerate(scripts, 1):
            print(f"   {i}. \"{script}\"")
    
    print(f"\n{PURPLE}{'='*70}{NC}\n")

def simulate_call():
    """Simulate a call with errors and coaching"""
    
    print_header("CONTACT CENTER COACHING - LIVE DEMONSTRATION")
    
    print(f"{CYAN}Starting demo call...{NC}")
    print(f"Rep: Demo Rep (Novice, 3 months tenure)")
    print(f"Customer: Business traveler (Impatient)\n")
    
    input("Press Enter to start the call...\n")
    
    # Turn 0: Customer opening
    print_transcript_turn(0, "customer", 
        "Hi, I just arrived at the hotel and they say you're overbooked. I don't have a room!")
    input(f"\n{YELLOW}Press Enter to continue...{NC}\n")
    
    # Turn 1: Rep response (ERROR: no empathy, missing verification)
    print_transcript_turn(1, "rep",
        "Can you give me your confirmation number?")
    
    print_detection("no_empathy", "medium", 1)
    print("   └─ Customer expressed frustration")
    print("   └─ Rep didn't acknowledge emotion")
    
    input(f"\n{YELLOW}Press Enter to see coaching...{NC}\n")
    
    print_coaching(
        "EmpathyCoach",
        "Empathy Opportunity Detected",
        "Customer expressed frustration but wasn't acknowledged. Before asking for information, show understanding of their situation.",
        [
            "I'm so sorry for the confusion. Let me help you fix this right away.",
            "I completely understand how frustrating this must be. I'm here to make this right."
        ],
        "medium"
    )
    
    input(f"{YELLOW}Press Enter to continue call...{NC}\n")
    
    # Turn 2: Customer provides info
    print_transcript_turn(2, "customer",
        "It's ABC123. This is ridiculous and very frustrating!")
    input(f"\n{YELLOW}Press Enter to continue...{NC}\n")
    
    # Turn 3: Rep accesses account (ERROR: missing verification)
    print_transcript_turn(3, "rep",
        "I see your booking here in the system.")
    
    print_detection("missing_verification", "high", 3)
    print("   └─ Accessed account without security check")
    print("   └─ COMPLIANCE VIOLATION")
    
    input(f"\n{YELLOW}Press Enter to see coaching...{NC}\n")
    
    print_coaching(
        "PolicyCoach",
        "Security Verification Required",
        "You accessed the customer account without verification. This is a compliance violation. Always verify identity before accessing sensitive information.",
        [
            "For security, let me first verify your last name and check-in date.",
            "Before I access your booking, can I confirm your account details?"
        ],
        "high"
    )
    
    input(f"{YELLOW}Press Enter to continue call...{NC}\n")
    
    # Turn 4: Customer demands refund
    print_transcript_turn(4, "customer",
        "This has ruined my trip. I want a full refund immediately.")
    input(f"\n{YELLOW}Press Enter to continue...{NC}\n")
    
    # Turn 5: Rep offers refund (ERROR: policy violation)
    print_transcript_turn(5, "rep",
        "Okay, I'll refund everything right now.")
    
    print_detection("policy_violation", "high", 5)
    print("   └─ Offered unauthorized refund")
    print("   └─ Didn't check policy or get approval")
    
    input(f"\n{YELLOW}Press Enter to see coaching...{NC}\n")
    
    print_coaching(
        "PolicyCoach",
        "Policy Check Required",
        "This refund requires manager approval. You must check what you're authorized to do before committing to compensation. Offer to find the best solution within policy.",
        [
            "Let me check our policy to see what options I can offer you.",
            "I want to help you with the best solution. Let me see what I'm authorized to do."
        ],
        "high"
    )
    
    input(f"{YELLOW}Press Enter to continue call...{NC}\n")
    
    # Turn 6: Customer mentions business travel
    print_transcript_turn(6, "customer",
        "Fine. I travel for business often so this is really disappointing.")
    input(f"\n{YELLOW}Press Enter to continue...{NC}\n")
    
    # Turn 7: Rep closes (ERROR: missed upsell)
    print_transcript_turn(7, "rep",
        "You'll get an email confirmation shortly. Goodbye.")
    
    print_detection("missed_upsell", "low", 7)
    print("   └─ Customer mentioned frequent travel")
    print("   └─ Opportunity to offer loyalty program")
    
    input(f"\n{YELLOW}Press Enter to see coaching...{NC}\n")
    
    print_coaching(
        "UpsellCoach",
        "Loyalty Program Opportunity",
        "Customer travels frequently for business - perfect opportunity for corporate rewards program. This helps prevent future issues and builds loyalty.",
        [
            "Since you travel for business often, would you like to hear about our corporate rewards program?",
            "I can note your preferences for future stays to ensure this doesn't happen again."
        ],
        "low"
    )
    
    # Summary
    print_header("DEMO COMPLETE - SUMMARY")
    
    print(f"{GREEN}✅ Call completed{NC}")
    print(f"\n{CYAN}Issues Detected:{NC}")
    print(f"  1. {YELLOW}no_empathy{NC} (medium) - Turn 1")
    print(f"  2. {RED}missing_verification{NC} (high) - Turn 3")
    print(f"  3. {RED}policy_violation{NC} (high) - Turn 5")
    print(f"  4. {BLUE}missed_upsell{NC} (low) - Turn 7")
    
    print(f"\n{CYAN}Coaching Delivered:{NC}")
    print(f"  • EmpathyCoach: Taught empathy acknowledgment")
    print(f"  • PolicyCoach: Enforced security verification (2x)")
    print(f"  • UpsellCoach: Suggested loyalty program")
    
    print(f"\n{GREEN}🎯 Key Takeaways:{NC}")
    print(f"  • Real-time detection: < 100ms per turn")
    print(f"  • Actionable coaching: Ready-to-use scripts")
    print(f"  • Context-aware: Tailored to novice rep")
    print(f"  • Severity-based: High-risk issues flagged immediately")
    
    print(f"\n{PURPLE}{'='*70}")
    print(f"Demo shows the complete detection → coaching flow")
    print(f"{'='*70}{NC}\n")

if __name__ == '__main__':
    try:
        simulate_call()
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Demo interrupted{NC}\n")
        sys.exit(0)

