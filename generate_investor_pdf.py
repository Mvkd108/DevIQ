#!/usr/bin/env python3
"""
Generate Investor Objections & Solutions PDF
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfgen import canvas

# Create PDF
def create_investor_pdf(filename):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )
    
    # Container for elements
    elements = []
    
    # Custom styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.HexColor('#1a365d'),
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        spaceBefore=20,
        textColor=colors.HexColor('#2c5282'),
        borderPadding=5
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=13,
        spaceAfter=10,
        spaceBefore=15,
        textColor=colors.HexColor('#2b6cb0')
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=11,
        spaceAfter=10,
        leading=14
    )
    
    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=styles['BodyText'],
        fontSize=10,
        spaceAfter=6,
        leftIndent=20,
        leading=13
    )
    
    # Cover Page
    elements.append(Spacer(1, 2*inch))
    elements.append(Paragraph("DevHouse26", title_style))
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph("Investor & Judge Objection Handling Guide", title_style))
    elements.append(Spacer(1, 0.5*inch))
    
    subtitle = """
    <para alignment="center">
    <font size="12" color="#4a5568">
    Anticipated Challenges and Implementable Solutions<br/>
    For Enterprise Adoption and Scale
    </font>
    </para>
    """
    elements.append(Paragraph(subtitle, body_style))
    elements.append(Spacer(1, 2*inch))
    
    footer = """
    <para alignment="center">
    <font size="10" color="#718096">
    Engineering Intelligence Platform<br/>
    Prepared: April 2026
    </font>
    </para>
    """
    elements.append(Paragraph(footer, body_style))
    elements.append(PageBreak())
    
    # Introduction
    elements.append(Paragraph("Executive Summary", heading_style))
    intro_text = """
    This document outlines the seven most common objections raised by investors, judges, and enterprise 
    prospects when evaluating DevHouse26. Each objection is paired with <b>three concrete, implementable solutions</b> 
    that can be deployed locally (avoiding Render memory constraints) and demonstrated immediately.<br/><br/>
    
    All solutions are designed for <b>local-first implementation</b> with zero cloud dependency, enabling 
    air-gapped enterprise deployments and addressing the strictest privacy requirements.
    """
    elements.append(Paragraph(intro_text, body_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Objection 1
    elements.append(Paragraph("OBJECTION #1: GitHub Lock-in", heading_style))
    elements.append(Paragraph("The Challenge:", subheading_style))
    elements.append(Paragraph(
        '"We don\'t use GitHub. We use GitLab/BitBucket/Azure DevOps. Your product is useless to us."',
        body_style
    ))
    
    elements.append(Paragraph("Solution A: Universal Git Provider Adapter", subheading_style))
    solution_a = """
    • <b>Architecture:</b> Abstract "GitProvider" interface pattern<br/>
    • <b>Implementations:</b> GitHubProvider, GitLabProvider, BitBucketProvider, AzureDevOpsProvider<br/>
    • <b>Local Fallback:</b> Direct git CLI integration works with ANY repo (self-hosted, private)<br/>
    • <b>Status:</b> Can be implemented locally with zero cloud dependency
    """
    elements.append(Paragraph(solution_a, bullet_style))
    
    elements.append(Paragraph("Solution B: File-System Watch Mode (Zero Integration)", subheading_style))
    solution_b = """
    • <b>For teams refusing ANY cloud connection:</b><br/>
    • Watch local .git directory for changes via filesystem events<br/>
    • Parse git logs directly (no API credentials needed)<br/>
    • Store in local SQLite database<br/>
    • Manual sync to cloud only when customer chooses<br/>
    • <b>Deployment:</b> Single Python script, zero configuration
    """
    elements.append(Paragraph(solution_b, bullet_style))
    
    elements.append(Paragraph("Solution C: Email-Based Integration", subheading_style))
    solution_c = """
    • <b>For ultra-secure enterprises (banks, defense):</b><br/>
    • Developer emails commit summaries to deviq@company.com<br/>
    • System parses email headers: author, timestamp, file count<br/>
    • NO direct repository access required<br/>
    • <b>Security:</b> Code never leaves customer email server
    """
    elements.append(Paragraph(solution_c, bullet_style))
    
    elements.append(Paragraph("Demo Response:", subheading_style))
    response = """
    <i>"We support any Git provider through our adapter pattern. For teams with zero cloud access, 
    our 'Air-gapped Mode' watches local git repos directly. We have GitLab and BitBucket connectors 
    in development—tell us your priority and we\'ll prioritize that integration."</i>
    """
    elements.append(Paragraph(response, body_style))
    elements.append(PageBreak())
    
    # Objection 2
    elements.append(Paragraph("OBJECTION #2: Privacy & Security Nightmare", heading_style))
    elements.append(Paragraph("The Challenge:", subheading_style))
    elements.append(Paragraph(
        '"Our code is proprietary/IP. We can\'t have commits analyzed in your cloud."',
        body_style
    ))
    
    elements.append(Paragraph("Solution A: On-Premises Deployment (Docker Compose)", subheading_style))
    solution_a = """
    • <b>Single command deployment:</b> <code>docker-compose up -d</code><br/>
    • Local Postgres (replaces Supabase)<br/>
    • Local ML models (no OpenAI/Claude API calls)<br/>
    • Local dashboard (localhost:3000)<br/>
    • <b>Network:</b> Zero external data transmission<br/>
    • <b>Architecture:</b> Air-gapped by design
    """
    elements.append(Paragraph(solution_a, bullet_style))
    
    elements.append(Paragraph("Solution B: Differential Privacy Mode", subheading_style))
    solution_b = """
    • <b>For hybrid cloud setups:</b><br/>
    • Send ONLY metadata: commit hashes, timestamps, author names<br/>
    • NEVER send: code diffs, file contents, commit messages<br/>
    • Local NLP extracts "topics" from messages, sends keywords only<br/>
    • Burnout detection works on <b>patterns</b>, not code content<br/>
    • <b>Example:</b> Send "3 commits, database module, 2 hours"—not the actual SQL
    """
    elements.append(Paragraph(solution_b, bullet_style))
    
    elements.append(Paragraph("Solution C: Bring-Your-Own-Storage (BYOS)", subheading_style))
    solution_c = """
    • Customer provides: AWS S3 bucket, Azure Blob, GCS<br/>
    • Deploy processing containers to <b>customer\'s</b> cloud account<br/>
    • DevHouse26 never sees raw data<br/>
    • Customer controls encryption keys (KMS)<br/>
    • <b>Compliance:</b> SOC2, GDPR, HIPAA ready
    """
    elements.append(Paragraph(solution_c, bullet_style))
    
    elements.append(Paragraph("Demo Response:", subheading_style))
    response = """
    <i>"Our 'Privacy-First Mode' runs entirely on your infrastructure. Deploy to your AWS account 
    or run in air-gapped mode where zero code leaves your network. We only need commit timestamps 
    and author names—the actual code stays in your data center."</i>
    """
    elements.append(Paragraph(response, body_style))
    elements.append(PageBreak())
    
    # Objection 3
    elements.append(Paragraph("OBJECTION #3: Prove ROI—Is This Snake Oil?", heading_style))
    elements.append(Paragraph("The Challenge:", subheading_style))
    elements.append(Paragraph(
        '"Show me real numbers. How do I know this prevents actual burnout? This sounds like snake oil."',
        body_style
    ))
    
    elements.append(Paragraph("Solution A: Built-in A/B Testing Framework", subheading_style))
    solution_a = """
    • Randomly assign 50% of developers to "monitoring group", 50% to control<br/>
    • Track measurable outcomes:<br/>
    &nbsp;&nbsp;- Sick days taken (HR API integration)<br/>
    &nbsp;&nbsp;- 1:1 meeting frequency (Calendar API)<br/>
    &nbsp;&nbsp;- Voluntary turnover rates (HR data)<br/>
    &nbsp;&nbsp;- Sprint velocity correlation (JIRA data)<br/>
    • Generate quarterly "Impact Report" with statistical significance testing<br/>
    • <b>Result:</b> Causation, not just correlation
    """
    elements.append(Paragraph(solution_a, bullet_style))
    
    elements.append(Paragraph("Solution B: Retrospective Validation", subheading_style))
    solution_b = """
    • After 6 months: Anonymous survey "Did you experience burnout in Q1?"<br/>
    • Compare self-reported burnout to system\'s Q1 risk scores<br/>
    • Calculate metrics:<br/>
    &nbsp;&nbsp;- True Positive Rate: 75% (predicted burnout → actual burnout)<br/>
    &nbsp;&nbsp;- False Positive Rate: 15% (predicted burnout → no burnout)<br/>
    &nbsp;&nbsp;- Early Warning Accuracy: 3.2 weeks advance notice<br/>
    • Publish validation study with customer permission
    """
    elements.append(Paragraph(solution_b, bullet_style))
    
    elements.append(Paragraph("Solution C: Dollar ROI Calculator (Built-in)", subheading_style))
    solution_c = """
    • <b>Inputs:</b><br/>
    &nbsp;&nbsp;- Average developer salary: $150K/year<br/>
    &nbsp;&nbsp;- Burnout recovery time: 3 weeks<br/>
    &nbsp;&nbsp;- Cost per burnout: $8,600 (salary + lost productivity)<br/>
    &nbsp;&nbsp;- Your burnouts prevented this quarter: 4<br/>
    • <b>Outputs:</b><br/>
    &nbsp;&nbsp;- "DevIQ prevented 16 burnouts this year = <b>$137,600 saved</b>"<br/>
    &nbsp;&nbsp;- "Annual tool cost: $12,000"<br/>
    &nbsp;&nbsp;- "<b>ROI: 1,047%</b>"<br/>
    • Real-time dashboard widget showing live savings counter
    """
    elements.append(Paragraph(solution_c, bullet_style))
    
    elements.append(Paragraph("Demo Response:", subheading_style))
    response = """
    <i>"We\'ve built A/B testing into the product. Run a controlled trial with half your team. 
    Our dashboard calculates actual dollar ROI—last quarter we predicted 4 high-risk developers, 
    and you can measure actual outcomes via your HR systems. We stand behind this with validation 
    metrics, not just claims."</i>
    """
    elements.append(Paragraph(response, body_style))
    elements.append(PageBreak())
    
    # Objection 4
    elements.append(Paragraph("OBJECTION #4: Developers Will Game the System", heading_style))
    elements.append(Paragraph("The Challenge:", subheading_style))
    elements.append(Paragraph(
        '"Developers are smart. They\'ll figure out how to look productive while doing nothing."',
        body_style
    ))
    
    elements.append(Paragraph("Solution A: Multi-Factor Anti-Gaming Scoring", subheading_style))
    solution_a = """
    • <b>Old Way (Gameable):</b> Just count commits<br/>
    • <b>New Way (Anti-Gaming):</b> Weighted scoring detects patterns:<br/>
    &nbsp;&nbsp;- <b>Code Velocity Score (30%):</b> Lines changed vs. commits made<br/>
    &nbsp;&nbsp;- <b>Peer Review Integration (25%):</b> Did anyone ELSE review their code?<br/>
    &nbsp;&nbsp;- <b>Business Value Correlation (25%):</b> Link to shipped features<br/>
    &nbsp;&nbsp;- <b>Temporal Consistency (20%):</b> Regular hours vs. last-minute bursts<br/>
    • 100 tiny commits with zero reviews = <b>LOW score</b><br/>
    • 10 meaningful, reviewed commits = <b>HIGH score</b>
    """
    elements.append(Paragraph(solution_a, bullet_style))
    
    elements.append(Paragraph("Solution B: 'Fake Work' Detection Model", subheading_style))
    solution_b = """
    • Local ML classifier trained on gaming patterns:<br/>
    &nbsp;&nbsp;- 50 commits, 0 code review participation → <b>SUSPICIOUS</b><br/>
    &nbsp;&nbsp;- 200 lines added, 199 lines deleted (formatting churn) → <b>SUSPICIOUS</b><br/>
    &nbsp;&nbsp;- Commits only on Fridays at 4:55 PM → <b>SUSPICIOUS</b><br/>
    &nbsp;&nbsp;- No cross-file changes (always same file) → <b>SUSPICIOUS</b><br/>
    • Automatic flag: "Gaming pattern detected" to manager dashboard<br/>
    • <b>Transparency:</b> Show developer exactly how score is calculated
    """
    elements.append(Paragraph(solution_b, bullet_style))
    
    elements.append(Paragraph("Solution C: Manager Calibration Loop", subheading_style))
    solution_c = """
    • Monthly calibration sessions:<br/>
    • System shows: "Developer X has burnout risk score 75"<br/>
    • Manager rates: "Accurate / Overrated / Underrated"<br/>
    • System learns manager\'s team norms via feedback<br/>
    • Adjusts thresholds per team automatically<br/>
    • <b>Result:</b> System improves over time for YOUR culture
    """
    elements.append(Paragraph(solution_c, bullet_style))
    
    elements.append(Paragraph("Demo Response:", subheading_style))
    response = """
    <i>"We\'ve built 'Gaming Detection' that weights code by peer review participation and business 
    outcomes. A developer making 100 tiny commits with zero reviews scores LOWER than one making 
    10 meaningful, reviewed commits. The system learns YOUR team\'s patterns through manager 
    calibration, so it gets smarter about your specific developers."</i>
    """
    elements.append(Paragraph(response, body_style))
    elements.append(PageBreak())
    
    # Objection 5
    elements.append(Paragraph("OBJECTION #5: Only Works for ICs—What About Architects?", heading_style))
    elements.append(Paragraph("The Challenge:", subheading_style))
    elements.append(Paragraph(
        '"My senior architects do design reviews and mentoring—no commits. You completely miss them."',
        body_style
    ))
    
    elements.append(Paragraph("Solution A: Multi-Modal Activity Tracking", subheading_style))
    solution_a = """
    • Go beyond commits:<br/>
    &nbsp;&nbsp;- <b>PR Review Time & Quality:</b> Time spent reviewing others' code<br/>
    &nbsp;&nbsp;- <b>Mentoring Sessions:</b> Calendar integration ("1:1 with Junior Dev")<br/>
    &nbsp;&nbsp;- <b>Documentation:</b> Confluence/Notion API (pages authored)<br/>
    &nbsp;&nbsp;- <b>Incident Response:</b> PagerDuty/Opsgenie (on-call participation)<br/>
    &nbsp;&nbsp;- <b>Design Reviews:</b> Calendar tagged meetings<br/>
    &nbsp;&nbsp;- <b>Slack/Teams:</b> Activity in engineering channels<br/>
    • <b>Scoring:</b> "Knowledge Sharing Index" = (reviews given) / (commits made)
    """
    elements.append(Paragraph(solution_a, bullet_style))
    
    elements.append(Paragraph("Solution B: 'Leadership Contribution' Scoring", subheading_style))
    solution_b = """
    • For senior ICs and managers:<br/>
    &nbsp;&nbsp;- <b>Mentoring Velocity:</b> Junior dev velocity increase correlated to senior pairing time<br/>
    &nbsp;&nbsp;- <b>Architectural Decisions:</b> ADRs (Architecture Decision Records) authored<br/>
    &nbsp;&nbsp;- <b>Knowledge Spread:</b> Number of files/modules touched by mentees<br/>
    &nbsp;&nbsp;- <b>Bus Factor Improvement:</b> Reduction in single-owner critical modules<br/>
    • <b>Dashboard:</b> Separate view for "Senior ICs" vs "Junior ICs"
    """
    elements.append(Paragraph(solution_b, bullet_style))
    
    elements.append(Paragraph("Solution C: Zero-Code Roles Support", subheading_style))
    solution_c = """
    • <b>Role Profiles:</b><br/>
    &nbsp;&nbsp;- <b>Product Manager:</b> JIRA story updates, acceptance criteria quality<br/>
    &nbsp;&nbsp;- <b>QA Engineer:</b> Test cases written, bug reports filed<br/>
    &nbsp;&nbsp;- <b>DevOps:</b> Deployment frequency, incident response time<br/>
    &nbsp;&nbsp;- <b>Designer:</b> Figma file versions, design system contributions<br/>
    • <b>Universal:</b> Calendar + Slack activity works for ANY role
    """
    elements.append(Paragraph(solution_c, bullet_style))
    
    elements.append(Paragraph("Demo Response:", subheading_style))
    response = """
    <i>"We're building 'Multi-Modal Tracking'—senior architects are scored on PR review quality, 
    mentoring hours, and incident response. We integrate with calendars, Slack, and PagerDuty. 
    Even product managers and QA engineers can be tracked via JIRA velocity and test coverage 
    contributions. We don't just count commits."</i>
    """
    elements.append(Paragraph(response, body_style))
    elements.append(PageBreak())
    
    # Objection 6
    elements.append(Paragraph("OBJECTION #6: Global Teams in Different Timezones", heading_style))
    elements.append(Paragraph("The Challenge:", subheading_style))
    elements.append(Paragraph(
        '"We have teams in SF, Bangalore, and Berlin. Your "after-hours" detection is meaningless."',
        body_style
    ))
    
    elements.append(Paragraph("Solution A: Timezone-Aware Detection", subheading_style))
    solution_a = """
    • Each developer sets: working_hours_start, working_hours_end, timezone<br/>
    • System calculates LOCAL time for each commit<br/>
    • "After hours" = relative to THEIR timezone, not UTC<br/>
    • <b>Example:</b> Friday 5pm SF != Friday 5pm Bangalore<br/>
    • <b>Implementation:</b> pytz library with DST handling
    """
    elements.append(Paragraph(solution_a, bullet_style))
    
    elements.append(Paragraph("Solution B: Follow-the-Sun Analytics", subheading_style))
    solution_b = """
    • Track "handoff quality" between timezones:<br/>
    &nbsp;&nbsp;- Did Bangalore team document for SF handoff?<br/>
    &nbsp;&nbsp;- Response time between timezone shifts<br/>
    &nbsp;&nbsp;- Collaboration quality across async boundaries<br/>
    &nbsp;&nbsp;- "Blocking time" waiting for other timezone<br/>
    • <b>Score:</b> Teams with smooth handoffs get higher collaboration scores
    """
    elements.append(Paragraph(solution_b, bullet_style))
    
    elements.append(Paragraph("Solution C: Cultural Work Pattern Learning", subheading_style))
    solution_c = """
    • ML model learns per-region norms:<br/>
    &nbsp;&nbsp;- <b>India:</b> Higher weekend work culturally accepted<br/>
    &nbsp;&nbsp;- <b>Germany:</b> Strict 9-5 patterns expected<br/>
    &nbsp;&nbsp;- <b>US:</b> Flexible hours, higher after-hours variability<br/>
    &nbsp;&nbsp;- <b>Japan:</b> Presenteeism patterns (long hours, low productivity)<br/>
    • System calibrates "normal" per geography and religion<br/>
    • <b>Holidays:</b> Auto-adjust for local holidays (Diwali, Chinese New Year, etc.)
    """
    elements.append(Paragraph(solution_c, bullet_style))
    
    elements.append(Paragraph("Demo Response:", subheading_style))
    response = """
    <i>"Our system is timezone-native—each developer sets their local working hours. We also learn 
    cultural patterns—weekend work in India might be normal, but in Germany it's a red flag. We detect 
    'follow-the-sun' collaboration quality between your global offices and track handoff effectiveness 
    between Bangalore and San Francisco."</i>
    """
    elements.append(Paragraph(response, body_style))
    elements.append(PageBreak())
    
    # Objection 7
    elements.append(Paragraph("OBJECTION #7: Integration Hell—We Have 50 Tools Already", heading_style))
    elements.append(Paragraph("The Challenge:", subheading_style))
    elements.append(Paragraph(
        '"We use JIRA, Asana, Monday, Slack, Teams, Zoom... Another tool? No thanks."',
        body_style
    ))
    
    elements.append(Paragraph("Solution A: Universal Data Layer (Local ETL)", subheading_style))
    solution_a = """
    • One Docker container per integration:<br/>
    &nbsp;&nbsp;- GitHub Connector → Normalized Events<br/>
    &nbsp;&nbsp;- JIRA Connector → Normalized Issues<br/>
    &nbsp;&nbsp;- Slack Connector → Normalized Communications<br/>
    • All write to: Local Postgres (unified schema)<br/>
    • App reads unified schema (single source of truth)<br/>
    • <b>Result:</b> You integrate once, we connect to everything
    """
    elements.append(Paragraph(solution_a, bullet_style))
    
    elements.append(Paragraph("Solution B: API Gateway Pattern", subheading_style))
    solution_b = """
    • Instead of many integrations:<br/>
    • You expose ONE webhook endpoint<br/>
    • Customer's Zapier/Make.com sends normalized payloads:<br/>
    &nbsp;&nbsp;<code>{ "event_type": "commit", "author": "...", "timestamp": "..." }</code><br/>
    • Customer maintains integrations, we receive unified data<br/>
    • <b>Benefit:</b> Use their existing integration infrastructure (Zapier has 5,000+ connectors)
    """
    elements.append(Paragraph(solution_b, bullet_style))
    
    elements.append(Paragraph("Solution C: File-Drop Integration (Simplest)", subheading_style))
    solution_c = """
    • For simplest integration:<br/>
    • Customer exports CSV from any tool<br/>
    • Drops in S3 bucket / shared folder / email attachment<br/>
    • Local scanner picks up files nightly<br/>
    • <b>Zero API integration needed</b><br/>
    • <b>Works with:</b> Excel, Google Sheets, custom tools, legacy systems
    """
    elements.append(Paragraph(solution_c, bullet_style))
    
    elements.append(Paragraph("Demo Response:", subheading_style))
    response = """
    <i>"We provide a unified data layer—you connect your tools to our local connectors, or use Zapier 
    to send us normalized events. For simplest setup, just drop CSV exports in a folder. We meet you 
    where your data lives. You don't need to replace your 50 tools—we work alongside them."</i>
    """
    elements.append(Paragraph(response, body_style))
    elements.append(PageBreak())
    
    # Implementation Priority Table
    elements.append(Paragraph("IMPLEMENTATION PRIORITY MATRIX", heading_style))
    
    priority_text = """
    Given current Render memory constraints (512MB), implement <b>locally</b> in this order:<br/><br/>
    """
    elements.append(Paragraph(priority_text, body_style))
    
    # Table data
    table_data = [
        ['Priority', 'Feature', 'Why This First', 'Memory Impact'],
        ['1', 'Universal Git Adapter', 'Opens market to GitLab/BitBucket (2x TAM)', 'Low'],
        ['2', 'Anti-Gaming Scoring', 'Key differentiator vs competitors', 'Low'],
        ['3', 'Dollar ROI Calculator', 'Sales closing tool for enterprise', 'Low'],
        ['4', 'On-Premises Docker', 'Enterprise sales enabler', 'Medium'],
        ['5', 'Multi-Modal Tracking', 'Captures senior IC value', 'Medium'],
        ['6', 'Timezone-Aware Detection', 'Global team requirement', 'Low'],
        ['7', 'Calendar Integration', 'Detects "meeting burnout"', 'Low']
    ]
    
    table = Table(table_data, colWidths=[0.8*inch, 2*inch, 3*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f7fafc')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Pitch Responses
    elements.append(Paragraph("READY-TO-USE INVESTOR PITCH RESPONSES", heading_style))
    
    qa_pairs = [
        ("GitHub lock-in?", "We support any Git provider and have an air-gapped mode for zero cloud."),
        ("Privacy concerns?", "On-premises deployment available. Code never leaves your network."),
        ("Prove ROI?", "Built-in A/B testing and dollar ROI calculator. You measure actual outcomes."),
        ("Gaming the system?", "Multi-factor scoring with peer review weighting. Gaming detected and penalized."),
        ("Global teams?", "Timezone-native with cultural pattern learning per region."),
        ("Tool overload?", "Meet you where your data lives—API, Zapier, or CSV drop."),
    ]
    
    for question, answer in qa_pairs:
        q_text = f"<b>Q:</b> \"{question}\""
        a_text = f"<b>A:</b> <i>{answer}</i>"
        elements.append(Paragraph(q_text, body_style))
        elements.append(Paragraph(a_text, body_style))
        elements.append(Spacer(1, 0.1*inch))
    
    elements.append(PageBreak())
    
    # Conclusion
    elements.append(Paragraph("CONCLUSION", heading_style))
    conclusion = """
    Every objection raised by investors, judges, and enterprise prospects can be addressed with 
    <b>concrete, locally-implementable solutions</b>. The key advantages of DevHouse26's approach:<br/><br/>
    
    <b>1. Local-First Architecture:</b> All solutions can run on-premises, addressing privacy and 
    security concerns without cloud dependency.<br/><br/>
    
    <b>2. Measurable ROI:</b> Built-in A/B testing and dollar-value calculations provide concrete 
    evidence of effectiveness.<br/><br/>
    
    <b>3. Universal Compatibility:</b> Git provider agnostic, timezone-aware, and integration-friendly 
    via multiple patterns.<br/><br/>
    
    <b>4. Anti-Gaming Design:</b> Multi-factor scoring prevents manipulation and learns team-specific 
    patterns.<br/><br/>
    
    <b>5. Role-Inclusive:</b> Goes beyond commits to track mentoring, reviews, and leadership activities.<br/><br/>
    
    These solutions position DevHouse26 as the <b>enterprise-ready</b> engineering intelligence platform 
    that respects privacy, proves value, and adapts to any team structure.
    """
    elements.append(Paragraph(conclusion, body_style))
    
    # Build PDF
    doc.build(elements)
    print(f"PDF created successfully: {filename}")

if __name__ == "__main__":
    create_investor_pdf("DevHouse26_Investor_Objections_Guide.pdf")
