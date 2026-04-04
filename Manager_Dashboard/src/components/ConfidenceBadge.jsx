/**
 * ConfidenceBadge Component
 * 
 * Displays confidence level and provenance source with consistent styling.
 * Shows visual indicators for data quality and trustworthiness.
 * 
 * @component
 * @param {Object} props
 * @param {number} props.confidence_score - 0.0 to 1.0
 * @param {'high'|'medium'|'low'} props.confidence_label - Confidence category
 * @param {'connector'|'inferred'|'heuristic'|'mock'|'mixed'} props.provenance - Data source
 * @param {boolean} [props.showDetails=false] - Show detailed evidence
 * @param {string[]} [props.evidence] - Evidence list for details view
 */

import { PROVENANCE_COLORS, CONFIDENCE_COLORS } from '../types/attribution.js';

function ConfidenceBadge({ 
  confidence_score = 0, 
  confidence_label = 'low',
  provenance = 'inferred',
  showDetails = false,
  evidence = []
}) {
  // Normalize confidence score
  const score = typeof confidence_score === 'number' ? confidence_score : parseFloat(confidence_score) || 0;
  const percentage = Math.round(score * 100);
  
  // Get colors based on provenance
  const provenanceColors = PROVENANCE_COLORS[provenance] || PROVENANCE_COLORS.inferred;
  const confidenceColors = CONFIDENCE_COLORS[confidence_label] || CONFIDENCE_COLORS.low;
  
  // Determine badge style
  const badgeStyle = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '4px 10px',
    borderRadius: '4px',
    fontSize: '12px',
    fontWeight: 500,
    backgroundColor: confidenceColors.bg,
    color: confidenceColors.text,
    border: `1px solid ${confidenceColors.border}`,
  };
  
  const provenanceStyle = {
    display: 'inline-block',
    padding: '2px 6px',
    borderRadius: '3px',
    fontSize: '10px',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    backgroundColor: provenanceColors.bg,
    color: provenanceColors.text,
    marginLeft: '4px',
  };
  
  const containerStyle = {
    display: 'inline-flex',
    flexDirection: 'column',
    gap: '4px',
  };
  
  const detailsStyle = {
    marginTop: '6px',
    padding: '8px',
    backgroundColor: '#f9fafb',
    borderRadius: '4px',
    fontSize: '11px',
    color: '#6b7280',
    maxWidth: '300px',
  };
  
  const evidenceItemStyle = {
    margin: '2px 0',
    paddingLeft: '12px',
    position: 'relative',
  };
  
  // Confidence label display
  const labelDisplay = confidence_label.charAt(0).toUpperCase() + confidence_label.slice(1);
  
  // Provenance label display
  const provenanceDisplay = provenanceColors.label;
  
  return (
    <div style={containerStyle}>
      <div style={badgeStyle}>
        <span>{labelDisplay}</span>
        <span style={{ opacity: 0.8 }}>({percentage}%)</span>
        <span style={provenanceStyle}>{provenanceDisplay}</span>
      </div>
      
      {showDetails && evidence.length > 0 && (
        <div style={detailsStyle}>
          <div style={{ fontWeight: 600, marginBottom: '4px', color: '#374151' }}>
            Evidence:
          </div>
          {evidence.map((item, idx) => (
            <div key={idx} style={evidenceItemStyle}>
              • {item}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default ConfidenceBadge;
