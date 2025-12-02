/**
 * Workflow Requirement Tracker
 * Ensures completeness at each workflow stage (TodoWrite-like mechanism)
 * Tracks that all requirements are met before progressing to next stage
 */

import { logger } from '../utils/logger.js';

export default class WorkflowRequirementTracker {
  constructor() {
    // Define requirements for each workflow stage
    this.stageRequirements = {
      interpret: {
        requirements: [
          'data_analyzed',           // Data/outputs were analyzed
          'insights_extracted',      // Key insights were extracted
          'patterns_identified',     // Patterns/trends were identified
          'context_provided'         // Context/meaning was provided
        ],
        description: 'Interpret existing outputs/data and explain what they mean',
        completionCriteria: {
          data_analyzed: 'Data or outputs were examined and understood',
          insights_extracted: 'Key insights were identified and explained',
          patterns_identified: 'Patterns, trends, or anomalies were detected',
          context_provided: 'Meaning and business context were provided'
        }
      },
      recommend: {
        requirements: [
          'actions_suggested',       // Specific actions were suggested
          'prioritized',             // Actions were prioritized
          'implications_considered', // Business implications were considered
          'rationale_provided'       // Reasoning for recommendations was given
        ],
        description: 'Provide actionable recommendations based on interpreted data',
        completionCriteria: {
          actions_suggested: 'Specific, actionable recommendations were provided',
          prioritized: 'Recommendations were ordered by priority/impact',
          implications_considered: 'Business implications and risks were addressed',
          rationale_provided: 'Reasoning behind recommendations was explained'
        }
      },
      'what-if': {
        requirements: [
          'scenarios_modeled',       // Alternative scenarios were explored
          'outcomes_calculated',      // Outcomes were calculated/estimated
          'risks_assessed',          // Risks were assessed
          'comparison_provided'       // Comparison between scenarios was provided
        ],
        description: 'Run simulations and explore "what if" scenarios',
        completionCriteria: {
          scenarios_modeled: 'Alternative scenarios were modeled',
          outcomes_calculated: 'Expected outcomes were calculated or estimated',
          risks_assessed: 'Risks and trade-offs were assessed',
          comparison_provided: 'Scenarios were compared to help decision-making'
        }
      },
      'full-llm': {
        requirements: [
          'knowledge_provided',      // Deep knowledge was provided
          'concepts_explained',      // Concepts were explained comprehensively
          'complexity_handled',      // Complex questions were addressed
          'context_maintained'       // Problem context was maintained
        ],
        description: 'Provide comprehensive knowledge, setup guidance, or handle complex questions',
        completionCriteria: {
          knowledge_provided: 'Deep knowledge or comprehensive information was provided',
          concepts_explained: 'Concepts were explained clearly and thoroughly',
          complexity_handled: 'Complex or nuanced questions were addressed',
          context_maintained: 'Response stayed within the problem space context'
        }
      }
    };

    // Track requirements per conversation/stage
    this.requirementTracking = new Map(); // conversationId -> { stage -> { requirements: {...}, decisions: [...] } }
  }

  /**
   * Initialize requirement tracking for a conversation
   */
  initializeTracking(conversationId, problemType, workflowStage) {
    const key = `${conversationId}-${workflowStage}`;
    
    if (!this.requirementTracking.has(key)) {
      const stageReqs = this.stageRequirements[workflowStage];
      
      if (!stageReqs) {
        logger.warn(`Unknown workflow stage: ${workflowStage}`);
        return null;
      }

      const tracking = {
        conversationId,
        problemType,
        workflowStage,
        requirements: {},
        decisions: [],
        startedAt: new Date().toISOString(),
        completedAt: null,
        isComplete: false
      };

      // Initialize all requirements as unmet
      stageReqs.requirements.forEach(req => {
        tracking.requirements[req] = {
          met: false,
          evidence: null,
          timestamp: null
        };
      });

      this.requirementTracking.set(key, tracking);
      logger.info(`📋 Initialized requirement tracking`, {
        conversationId,
        problemType,
        workflowStage,
        requirementsCount: stageReqs.requirements.length
      });
    }

    return this.requirementTracking.get(key);
  }

  /**
   * Mark a requirement as met
   */
  markRequirementMet(conversationId, workflowStage, requirement, evidence = null) {
    const key = `${conversationId}-${workflowStage}`;
    const tracking = this.requirementTracking.get(key);

    if (!tracking) {
      logger.warn(`No tracking found for ${key}`);
      return false;
    }

    if (!tracking.requirements[requirement]) {
      logger.warn(`Unknown requirement: ${requirement} for stage: ${workflowStage}`);
      return false;
    }

    tracking.requirements[requirement] = {
      met: true,
      evidence: evidence || `Requirement met at ${new Date().toISOString()}`,
      timestamp: new Date().toISOString()
    };

    logger.debug(`✅ Requirement met: ${requirement}`, { conversationId, workflowStage });

    // Check if all requirements are now met
    this.checkCompletion(conversationId, workflowStage);

    return true;
  }

  /**
   * Record a decision with rationale
   */
  recordDecision(conversationId, workflowStage, decision, rationale, context = {}) {
    const key = `${conversationId}-${workflowStage}`;
    const tracking = this.requirementTracking.get(key);

    if (!tracking) {
      logger.warn(`No tracking found for ${key}`);
      return false;
    }

    tracking.decisions.push({
      decision,
      rationale,
      context,
      timestamp: new Date().toISOString()
    });

    logger.info(`📝 Decision recorded`, {
      conversationId,
      workflowStage,
      decision,
      rationale: rationale.substring(0, 100) + '...'
    });

    return true;
  }

  /**
   * Check if all requirements for a stage are met
   * Returns completion status and unmet requirements
   */
  checkCompletion(conversationId, workflowStage) {
    const key = `${conversationId}-${workflowStage}`;
    const tracking = this.requirementTracking.get(key);

    if (!tracking) {
      return { isComplete: false, unmetRequirements: [] };
    }

    const allMet = Object.values(tracking.requirements).every(req => req.met);
    const unmetRequirements = Object.entries(tracking.requirements)
      .filter(([_, req]) => !req.met)
      .map(([reqName, _]) => reqName);

    if (allMet && !tracking.isComplete) {
      tracking.isComplete = true;
      tracking.completedAt = new Date().toISOString();
      
      logger.info(`🎯 Stage requirements complete`, {
        conversationId,
        workflowStage,
        requirementsMet: Object.keys(tracking.requirements).length
      });
    } else if (!allMet && tracking.isComplete) {
      // If requirements become unmet (shouldn't happen, but handle it)
      tracking.isComplete = false;
      tracking.completedAt = null;
    }

    return { 
      isComplete: allMet, 
      unmetRequirements,
      totalRequirements: Object.keys(tracking.requirements).length,
      metRequirements: Object.keys(tracking.requirements).length - unmetRequirements.length
    };
  }

  /**
   * Get unmet requirements with descriptions for improvement feedback
   */
  getUnmetRequirementsWithDescriptions(conversationId, workflowStage) {
    const key = `${conversationId}-${workflowStage}`;
    const tracking = this.requirementTracking.get(key);
    const stageReqs = this.stageRequirements[workflowStage];

    if (!tracking || !stageReqs) {
      return [];
    }

    return Object.entries(tracking.requirements)
      .filter(([_, req]) => !req.met)
      .map(([reqName, _]) => ({
        requirement: reqName,
        description: stageReqs.completionCriteria[reqName] || 'N/A',
        whatIsMissing: this.getRequirementGuidance(reqName, workflowStage)
      }));
  }

  /**
   * Get guidance on what's needed to meet a requirement
   */
  getRequirementGuidance(requirement, workflowStage) {
    const guidance = {
      'data_analyzed': 'The response should explicitly analyze or examine the data provided. Include phrases like "analyzing the data shows..." or "when we examine these numbers..."',
      'insights_extracted': 'The response should identify key insights or findings. Include phrases like "key insight is..." or "important finding..."',
      'patterns_identified': 'The response should identify patterns, trends, or anomalies. Include phrases like "the pattern shows..." or "this trend indicates..."',
      'context_provided': 'The response should explain what the data means in business context. Include phrases like "this means..." or "this indicates..."',
      'actions_suggested': 'The response should suggest specific, actionable steps. Include phrases like "I recommend..." or "you should..."',
      'prioritized': 'The response should prioritize recommendations. Include phrases like "most important..." or "first, you should..."',
      'implications_considered': 'The response should consider business implications. Include phrases like "this will impact..." or "the implications are..."',
      'rationale_provided': 'The response should explain why recommendations are made. Include phrases like "because..." or "the reason is..."',
      'scenarios_modeled': 'The response should explore alternative scenarios. Include phrases like "if we..." or "what if..."',
      'outcomes_calculated': 'The response should calculate or estimate outcomes. Include phrases like "this would result in..." or "expected outcome is..."',
      'risks_assessed': 'The response should assess risks. Include phrases like "the risk is..." or "potential concern..."',
      'comparison_provided': 'The response should compare scenarios. Include phrases like "compared to..." or "versus..."',
      'knowledge_provided': 'The response should provide comprehensive knowledge. Ensure the response is substantial and informative.',
      'concepts_explained': 'The response should explain concepts clearly. Include phrases like "this means..." or "in other words..."',
      'complexity_handled': 'The response should address complex aspects. Include phrases like "this is complex because..." or "the nuanced aspect is..."',
      'context_maintained': 'The response should stay within the problem space. Reference the original problem type and context.'
    };

    return guidance[requirement] || 'This requirement needs to be addressed to ensure completeness.';
  }

  /**
   * Get completion status for a stage
   */
  getCompletionStatus(conversationId, workflowStage) {
    const key = `${conversationId}-${workflowStage}`;
    const tracking = this.requirementTracking.get(key);

    if (!tracking) {
      return null;
    }

    const requirements = Object.entries(tracking.requirements).map(([req, status]) => ({
      requirement: req,
      met: status.met,
      evidence: status.evidence,
      timestamp: status.timestamp,
      description: this.stageRequirements[workflowStage]?.completionCriteria[req] || 'N/A'
    }));

    const metCount = requirements.filter(r => r.met).length;
    const totalCount = requirements.length;

    return {
      workflowStage,
      isComplete: tracking.isComplete,
      progress: {
        met: metCount,
        total: totalCount,
        percentage: Math.round((metCount / totalCount) * 100)
      },
      requirements,
      decisions: tracking.decisions,
      startedAt: tracking.startedAt,
      completedAt: tracking.completedAt
    };
  }

  /**
   * Get unmet requirements for a stage
   */
  getUnmetRequirements(conversationId, workflowStage) {
    const status = this.getCompletionStatus(conversationId, workflowStage);
    
    if (!status) {
      return null;
    }

    return status.requirements.filter(r => !r.met);
  }

  /**
   * Validate that all requirements are met (enforcement)
   * Returns validation result with actionable feedback
   */
  validateCompleteness(conversationId, workflowStage) {
    const completionCheck = this.checkCompletion(conversationId, workflowStage);
    const status = this.getCompletionStatus(conversationId, workflowStage);
    
    if (!status) {
      return {
        isValid: false,
        error: 'No tracking found for this conversation/stage'
      };
    }

    const unmetWithGuidance = this.getUnmetRequirementsWithDescriptions(conversationId, workflowStage);

    return {
      isValid: completionCheck.isComplete,
      isComplete: completionCheck.isComplete,
      progress: status.progress,
      unmetRequirements: completionCheck.unmetRequirements,
      unmetRequirementsDetails: unmetWithGuidance,
      message: completionCheck.isComplete
        ? '✅ All requirements met - response is production-ready'
        : `⚠️ Only ${completionCheck.metRequirements}/${completionCheck.totalRequirements} requirements met. Response may be incomplete.`,
      recommendations: unmetWithGuidance.map(req => ({
        requirement: req.requirement,
        whatToAdd: req.whatIsMissing
      }))
    };
  }

  /**
   * Analyze response to automatically detect met requirements
   */
  analyzeResponseForRequirements(conversationId, workflowStage, responseText, problemType) {
    const stageReqs = this.stageRequirements[workflowStage];
    
    if (!stageReqs) {
      return;
    }

    const lowerResponse = responseText.toLowerCase();
    const detected = [];

    // Analyze response for each requirement
    stageReqs.requirements.forEach(requirement => {
      let met = false;
      let evidence = null;

      switch (requirement) {
        case 'data_analyzed':
          // More comprehensive detection for data analysis
          met = /(analyzed|examined|reviewed|looked at|studied|analyzing|analysis|analyze).*(data|results|outputs|metrics|numbers|figures|revenue|sales|inventory|units|trend|quarter|Q1|Q2|Q3|Q4)/i.test(responseText) ||
                /(data|results|outputs|metrics|numbers|figures|revenue|sales).*(show|indicate|reveal|suggest|mean|demonstrate|reflect)/i.test(responseText) ||
                /(Q1|Q2|Q3|Q4|\$|percent|%|units|revenue|sales).*(was|is|are|shows|indicates|reveals)/i.test(responseText);
          if (met) evidence = 'Response mentions analyzing data/results or references specific data points';
          break;

        case 'insights_extracted':
          met = /(insight|finding|key|important|notable|significant|pattern|trend)/i.test(responseText);
          if (met) evidence = 'Response contains insights or findings';
          break;

        case 'patterns_identified':
          met = /(pattern|trend|anomaly|deviation|change|increase|decrease|drop|rise)/i.test(responseText);
          if (met) evidence = 'Response identifies patterns or trends';
          break;

        case 'context_provided':
          met = /(mean|indicate|suggest|show|reveal|imply|signify)/i.test(responseText);
          if (met) evidence = 'Response provides context or meaning';
          break;

        case 'actions_suggested':
          met = /(recommend|suggest|should|action|step|approach|strategy|solution)/i.test(responseText);
          if (met) evidence = 'Response suggests actions or recommendations';
          break;

        case 'prioritized':
          met = /(priority|first|most important|critical|urgent|focus|key|primary)/i.test(responseText);
          if (met) evidence = 'Response includes prioritization';
          break;

        case 'implications_considered':
          met = /(implication|impact|effect|consequence|risk|benefit|trade-off|consideration)/i.test(responseText);
          if (met) evidence = 'Response considers implications or impacts';
          break;

        case 'rationale_provided':
          met = /(because|due to|reason|rationale|why|since|as a result)/i.test(responseText);
          if (met) evidence = 'Response provides reasoning or rationale';
          break;

        case 'scenarios_modeled':
          met = /(scenario|what if|if we|alternative|option|approach|strategy)/i.test(responseText);
          if (met) evidence = 'Response explores scenarios or alternatives';
          break;

        case 'outcomes_calculated':
          met = /(projected|expected|estimate|calculate|result|outcome|would|could|might)/i.test(responseText);
          if (met) evidence = 'Response calculates or estimates outcomes';
          break;

        case 'risks_assessed':
          met = /(risk|challenge|concern|potential issue|trade-off|downside|limitation)/i.test(responseText);
          if (met) evidence = 'Response assesses risks or concerns';
          break;

        case 'comparison_provided':
          met = /(compare|versus|vs|better|worse|advantage|disadvantage|difference)/i.test(responseText);
          if (met) evidence = 'Response provides comparisons';
          break;

        case 'knowledge_provided':
          met = responseText.length > 200; // Substantial response indicates knowledge
          if (met) evidence = 'Response provides comprehensive knowledge';
          break;

        case 'concepts_explained':
          met = /(explain|define|describe|overview|concept|understanding|means)/i.test(responseText);
          if (met) evidence = 'Response explains concepts';
          break;

        case 'complexity_handled':
          // Detect explicit complexity phrasing OR common operational complexity indicators
          const complexityPhrases = /(complex|nuanced|detailed|comprehensive|thorough|in-depth|edge\s*cases?|trade-?offs?)/i;
          const operationalComplexityPatterns = [
            /thresholds?/i,
            /calibration/i,
            /sensitivity/i,
            /precision/i,
            /recall/i,
            /false\s*positives?/i,
            /false\s*negatives?/i,
            /seasonality|seasonal/i,
            /latency|delay|freshness/i,
            /drift|data\s*drift|concept\s*drift/i,
            /alert\s*fatigue|fatigue/i,
            /noise|variance/i,
            /outliers?/i,
            /escalation|escalate/i,
            /\bSLA\b/i,
            /runbook|playbook/i,
            /constraint|constraints|limit|limitations/i,
            /integration|backfill/i
          ];
          met = complexityPhrases.test(responseText) || operationalComplexityPatterns.some(r => r.test(responseText));
          if (met) evidence = 'Response addresses complexity, edge cases, or operational trade-offs';
          break;

        case 'context_maintained':
          // Check if response mentions the problem type or problem space
          const problemKeywords = {
            alert: ['alert', 'risk', 'warning', 'notify'],
            monitor: ['monitor', 'track', 'watch', 'observe'],
            understand: ['understand', 'analyze', 'explain'],
            solve: ['solve', 'fix', 'address', 'resolve'],
            automate: ['automate', 'automatic', 'workflow', 'process']
          };
          const keywords = problemKeywords[problemType] || [];
          met = keywords.some(kw => lowerResponse.includes(kw));
          if (met) evidence = 'Response maintains problem context';
          break;
      }

      if (met) {
        this.markRequirementMet(conversationId, workflowStage, requirement, evidence);
        detected.push(requirement);
      }
    });

    if (detected.length > 0) {
      logger.info(`🔍 Auto-detected ${detected.length} requirements met`, {
        conversationId,
        workflowStage,
        requirements: detected
      });
    }

    return detected;
  }

  /**
   * Get summary of all tracked conversations
   */
  getSummary() {
    const summary = {
      totalTracked: this.requirementTracking.size,
      byStage: {},
      completionRates: {}
    };

    this.requirementTracking.forEach((tracking, key) => {
      const stage = tracking.workflowStage;
      
      if (!summary.byStage[stage]) {
        summary.byStage[stage] = {
          total: 0,
          complete: 0,
          incomplete: 0
        };
      }

      summary.byStage[stage].total++;
      if (tracking.isComplete) {
        summary.byStage[stage].complete++;
      } else {
        summary.byStage[stage].incomplete++;
      }
    });

    // Calculate completion rates
    Object.keys(summary.byStage).forEach(stage => {
      const stats = summary.byStage[stage];
      summary.completionRates[stage] = stats.total > 0
        ? Math.round((stats.complete / stats.total) * 100)
        : 0;
    });

    return summary;
  }

  /**
   * Clear tracking for a conversation (cleanup)
   */
  clearTracking(conversationId) {
    const keysToDelete = [];
    this.requirementTracking.forEach((tracking, key) => {
      if (tracking.conversationId === conversationId) {
        keysToDelete.push(key);
      }
    });

    keysToDelete.forEach(key => this.requirementTracking.delete(key));
    
    if (keysToDelete.length > 0) {
      logger.info(`🧹 Cleared tracking for conversation`, {
        conversationId,
        cleared: keysToDelete.length
      });
    }
  }
}

