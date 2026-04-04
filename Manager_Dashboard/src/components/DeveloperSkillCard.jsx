/**
 * DeveloperSkillCard Component
 * 
 * Displays a compact skill snapshot for a developer.
 * Shows top 3 skills with scores, confidence indicators,
 * and fallback/expert discovery CTAs.
 * 
 * @component
 * @param {Object} props
 * @param {string} props.developerId - Developer identifier
 * @param {Object} props.skillsData - Skills data from API
 */

import { useState, useEffect } from 'react';
import ConfidenceBadge from './ConfidenceBadge';

function DeveloperSkillCard({ developerId, skillsData }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Default to provided data or empty state
  const [skills, setSkills] = useState(skillsData?.skills || []);
  
  useEffect(() => {
    if (skillsData) {
      setSkills(skillsData.skills || []);
    }
  }, [skillsData, developerId]);
  
  // Get top 3 skills
  const topSkills = skills.slice(0, 3);
  const hasSkills = topSkills.length > 0;
  const topSkill = topSkills[0];
  
  // Skill category colors
  const categoryColors = {
    technical: '#3b82f6',  // blue
    domain: '#10b981',     // green
    process: '#f59e0b',    // amber
  };
  
  const cardStyle = {
    backgroundColor: '#ffffff',
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
    padding: '16px',
    maxWidth: '320px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
  };
  
  const headerStyle = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px',
    borderBottom: '1px solid #f3f4f6',
    paddingBottom: '8px',
  };
  
  const titleStyle = {
    fontSize: '14px',
    fontWeight: 600,
    color: '#111827',
    margin: 0,
  };
  
  const skillListStyle = {
    listStyle: 'none',
    padding: 0,
    margin: '0 0 12px 0',
  };
  
  const skillItemStyle = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '8px 0',
    borderBottom: '1px solid #f9fafb',
  };
  
  const skillNameStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '13px',
    color: '#374151',
  };
  
  const categoryDotStyle = (category) => ({
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    backgroundColor: categoryColors[category] || '#6b7280',
  });
  
  const scoreStyle = {
    fontSize: '12px',
    fontWeight: 600,
    color: '#6b7280',
  };
  
  const actionsStyle = {
    display: 'flex',
    gap: '8px',
    marginTop: '12px',
  };
  
  const buttonStyle = {
    flex: 1,
    padding: '6px 12px',
    fontSize: '11px',
    fontWeight: 500,
    borderRadius: '4px',
    border: '1px solid #d1d5db',
    backgroundColor: '#ffffff',
    color: '#374151',
    cursor: 'pointer',
    textAlign: 'center',
  };
  
  const primaryButtonStyle = {
    ...buttonStyle,
    backgroundColor: '#3b82f6',
    color: '#ffffff',
    borderColor: '#3b82f6',
  };
  
  const emptyStateStyle = {
    textAlign: 'center',
    padding: '20px',
    color: '#6b7280',
    fontSize: '13px',
  };
  
  const handleUseAsFallback = () => {
    // Emit event for parent components
    if (window.EventBus) {
      window.EventBus.emit('skill:fallback-selected', {
        developerId,
        topSkill: topSkill?.skill_tag,
      });
    }
    console.log(`[SkillCard] Using ${developerId} as fallback for ${topSkill?.skill_tag}`);
  };
  
  const handleFindExperts = () => {
    // Navigate to expert finder or emit event
    if (window.EventBus) {
      window.EventBus.emit('skill:find-experts', {
        developerId,
        skillTag: topSkill?.skill_tag,
      });
    }
    console.log(`[SkillCard] Finding experts similar to ${developerId}`);
  };
  
  if (loading) {
    return (
      <div style={cardStyle}>
        <div style={emptyStateStyle}>Loading skills...</div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div style={cardStyle}>
        <div style={emptyStateStyle}>Error loading skills</div>
      </div>
    );
  }
  
  if (!hasSkills) {
    return (
      <div style={cardStyle}>
        <div style={headerStyle}>
          <h4 style={titleStyle}>Developer Skills</h4>
        </div>
        <div style={emptyStateStyle}>
          No skill data available for this developer.
          <br />
          <small style={{ color: '#9ca3af' }}>
            Skills are inferred from commit history.
          </small>
        </div>
      </div>
    );
  }
  
  return (
    <div style={cardStyle}>
      <div style={headerStyle}>
        <h4 style={titleStyle}>Top Skills</h4>
        {topSkill && (
          <ConfidenceBadge
            confidence_score={topSkill.confidence_score}
            confidence_label={topSkill.confidence_label}
            provenance="inferred"
            showDetails={false}
          />
        )}
      </div>
      
      <ul style={skillListStyle}>
        {topSkills.map((skill, idx) => (
          <li key={idx} style={skillItemStyle}>
            <span style={skillNameStyle}>
              <span style={categoryDotStyle(skill.skill_category)} />
              {skill.skill_tag.replace(/_/g, ' ')}
            </span>
            <span style={scoreStyle}>{Math.round(skill.score)}%</span>
          </li>
        ))}
      </ul>
      
      <div style={actionsStyle}>
        <button
          style={primaryButtonStyle}
          onClick={handleUseAsFallback}
          title="Use this developer as fallback for these skills"
        >
          Use as Fallback
        </button>
        <button
          style={buttonStyle}
          onClick={handleFindExperts}
          title="Find developers with similar skills"
        >
          Find Similar
        </button>
      </div>
    </div>
  );
}

export default DeveloperSkillCard;
