from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import BarChart, Reference
from openpyxl.utils import get_column_letter
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image as RLImage
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from collections import Counter
from pathlib import Path
import string, json, re, csv, textwrap, subprocess, shutil

ROOT = Path('/home/ubuntu/carbon_tracker')
OUT = ROOT / 'submission'
OUT.mkdir(exist_ok=True)

TITLE = 'Household Carbon Footprint & Target Tracker'
DOMAIN = 'Sustainability & Green Tech'
AUTHOR = 'Manus AI'
DATE = '25-08-2026'

# ---------- Shared helpers ----------
def shade_cell(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = tcPr.find(qn('w:shd'))
    if shd is None:
        shd = OxmlElement('w:shd'); tcPr.append(shd)
    shd.set(qn('w:fill'), fill)

def set_cell_text(cell, text, bold=False, color=None, size=9):
    cell.text = ''
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(str(text)); r.bold = bold; r.font.size = Pt(size)
    if color: r.font.color.rgb = RGBColor(*color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

def set_doc_defaults(doc):
    sec = doc.sections[0]
    sec.top_margin = Inches(0.65); sec.bottom_margin = Inches(0.65)
    sec.left_margin = Inches(0.65); sec.right_margin = Inches(0.65)
    styles = doc.styles
    styles['Normal'].font.name = 'Aptos'; styles['Normal'].font.size = Pt(10)
    styles['Heading 1'].font.name = 'Aptos Display'; styles['Heading 1'].font.size = Pt(17); styles['Heading 1'].font.color.rgb = RGBColor(20, 93, 72)
    styles['Heading 2'].font.name = 'Aptos Display'; styles['Heading 2'].font.size = Pt(13); styles['Heading 2'].font.color.rgb = RGBColor(31, 111, 83)
    styles['Heading 3'].font.name = 'Aptos'; styles['Heading 3'].font.size = Pt(11); styles['Heading 3'].font.color.rgb = RGBColor(58, 88, 77)
    header = sec.header.paragraphs[0]
    header.text = f'{TITLE}  |  {DOMAIN}'
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for r in header.runs: r.font.size = Pt(8); r.font.color.rgb = RGBColor(100,100,100)
    footer = sec.footer.paragraphs[0]
    footer.text = f'Prepared by {AUTHOR}  |  {DATE}'
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for r in footer.runs: r.font.size = Pt(8); r.font.color.rgb = RGBColor(100,100,100)

def title_block(doc, subtitle):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(TITLE); r.bold=True; r.font.size=Pt(22); r.font.color.rgb=RGBColor(20,93,72)
    p = doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=p.add_run(subtitle); r.bold=True; r.font.size=Pt(13); r.font.color.rgb=RGBColor(55,75,65)
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(f'Domain: {DOMAIN}  |  Prepared by: {AUTHOR}  |  Date: {DATE}').italic=True
    doc.add_paragraph()

def add_table(doc, headers, rows, widths=None, font_size=8):
    table=doc.add_table(rows=1, cols=len(headers)); table.alignment=WD_TABLE_ALIGNMENT.CENTER; table.style='Table Grid'
    for i,h in enumerate(headers):
        set_cell_text(table.rows[0].cells[i], h, bold=True, color=(255,255,255), size=font_size)
        shade_cell(table.rows[0].cells[i], '145D48')
    for row in rows:
        cells=table.add_row().cells
        for i,val in enumerate(row): set_cell_text(cells[i], val, size=font_size)
    if widths:
        for row in table.rows:
            for i,w in enumerate(widths): row.cells[i].width=Inches(w)
    return table

def add_bullets(doc, items):
    for item in items:
        p=doc.add_paragraph(style='List Bullet'); p.paragraph_format.space_after=Pt(2); p.add_run(item)

def save_doc(doc, path):
    set_doc_defaults(doc); doc.save(path)

# ---------- Lab 1: Requirements ----------
requirements = [
 ['FR-001','Functional','The system shall allow an authorized household member to create and maintain a household profile containing household size, location, and selected measurement units.','High','A profile can be saved with valid values; reopening the profile displays the same values; invalid or missing mandatory values prevent saving and show an explanatory message.','A profile is needed to contextualize calculations and personalize progress tracking.','Peer review: specify mandatory fields and validation behavior; incorporated.'],
 ['FR-002','Functional','The system shall allow a household member to record monthly activity data for at least electricity, stationary fuel, transport, and waste categories.','High','For each category, the user can enter a value, unit, and month; after saving, the entry appears in the selected month and can be edited or deleted.','Structured activity data is the input needed to calculate a household footprint.','Peer review: require month, unit, and category to avoid ambiguous entries; incorporated.'],
 ['FR-003','Functional','The system shall calculate the household carbon footprint in kilograms of carbon-dioxide equivalent (kg CO2e) from saved activity data and the applicable emission factors.','High','Given a saved activity value and factor, the displayed category result equals activity multiplied by factor within a rounding tolerance of 0.01 kg CO2e; the total equals the sum of displayed categories.','Automated calculation turns raw household activity into an understandable footprint measure.','Peer review: define formula and rounding tolerance; incorporated.'],
 ['FR-004','Functional','The system shall allow a household member to set a baseline period, a reduction target percentage, and a target date.','High','The system saves a target only when the percentage is between 0% and 100% and the target date is after the baseline period; the target summary shows the baseline, target value, and date.','Explicit targets make the tracker actionable rather than purely descriptive.','Peer review: add range and date validation; incorporated.'],
 ['FR-005','Functional','The system shall display progress toward the active target using actual-versus-target values, category breakdown, trend history, and recorded reduction actions.','Medium','For a household with at least two periods, the dashboard displays actual total, target total, variance, trend direction, and action history; values update after a new activity record is saved.','Feedback and history help households understand whether actions are working.','Peer review: specify minimum data and update trigger; incorporated.'],
 ['NFR-001','Nonfunctional','The system shall display a saved monthly footprint dashboard within 3 seconds for a household with up to 24 months of data.','High','In 10 consecutive test runs on the reference environment, the dashboard loads completely in under 3 seconds for the stated data volume.','Fast feedback supports routine use and prevents abandonment.','Peer review: define dataset size, environment, and repeated-run pass rule; incorporated.'],
 ['NFR-002','Nonfunctional','The system shall protect household data in transit and at rest and shall restrict editing and export actions to authenticated, authorized users.','High','Unauthenticated requests to household data return an access-denied result; authenticated users cannot access another household’s records; transport uses HTTPS and stored records are encrypted by the deployment configuration.','Household energy and mobility information can be sensitive and must be protected.','Peer review: make access-control checks observable and testable; incorporated.'],
]

# Requirements docx
req_doc=Document(); title_block(req_doc,'Lab 1 — Requirements Table / Software Requirements Specification Extract')
req_doc.add_heading('Project context', level=1)
req_doc.add_paragraph('This requirements set adapts the Lab 1 requirements-engineering exercise to the specified Sustainability & Green Tech project. The tracker helps a household enter activity data, calculate a carbon footprint, define a reduction target, and monitor progress over time. Exactly five functional requirements and two nonfunctional requirements are provided, as required by the handout.')
req_doc.add_heading('Requirements table', level=1)
add_table(req_doc,['Req ID','Type','Description (“The system shall…”)','Priority','Acceptance Criteria','Rationale','Comments'],requirements,widths=[0.55,0.65,2.25,0.55,2.35,1.55,1.65],font_size=7)
req_doc.add_heading('Peer-critique summary', level=1)
req_doc.add_paragraph('The peer-review pass checked each requirement for clarity, testability, and relevance. The comments column records the revision applied to remove ambiguity, define measurable conditions, and keep each statement within the project scope.')
req_doc.add_heading('Scope assumptions', level=1)
add_bullets(req_doc,[
 'The system uses configured emission factors; the factors are treated as versioned configuration data rather than hard-coded user input.',
 'A household may have one active target at a time, while historical targets and footprint periods remain viewable.',
 'The first release records user-entered activity data; automatic utility-account integrations are outside the minimum lab scope.',
 'The unit kg CO2e is used consistently in the requirements and dashboard labels.'
])
save_doc(req_doc,OUT/'Lab1_Requirements_Table.docx')

# Requirements Excel
wb=Workbook(); ws=wb.active; ws.title='Requirements'
ws.append(['Req ID','Type','Description (“The system shall…”)','Priority','Acceptance Criteria','Rationale','Comments'])
for row in requirements: ws.append(row)
for cell in ws[1]: cell.font=Font(bold=True,color='FFFFFF'); cell.fill=PatternFill('solid',fgColor='145D48'); cell.alignment=Alignment(wrap_text=True,vertical='center')
for row in ws.iter_rows():
    for cell in row: cell.alignment=Alignment(wrap_text=True,vertical='top'); cell.border=Border(bottom=Side(style='thin',color='D9E5DF'))
widths=[12,15,48,12,58,38,42]
for i,w in enumerate(widths,1): ws.column_dimensions[get_column_letter(i)].width=w
ws.freeze_panes='A2'; ws.auto_filter.ref=ws.dimensions
for r in range(2,ws.max_row+1): ws.row_dimensions[r].height=92
ws2=wb.create_sheet('Traceability')
ws2.append(['Requirement','Primary Use Case(s)','Actor(s)','Verification Method'])
trace=[
 ['FR-001','UC-01 Manage Household Profile','Household Member; Household Administrator','Functional test and inspection'],
 ['FR-002','UC-02 Record Activity Data','Household Member','Functional test with save/edit/delete cases'],
 ['FR-003','UC-03 Calculate Footprint','Household Member; Emission-Factor Provider','Calculation test against known values'],
 ['FR-004','UC-04 Set Reduction Target','Household Member','Validation and persistence test'],
 ['FR-005','UC-05 Track Progress; UC-06 Log Reduction Action','Household Member','Dashboard acceptance test'],
 ['NFR-001','UC-05 Track Progress','Household Member','Performance test: 10 repeated runs'],
 ['NFR-002','All data-bearing use cases','All authenticated actors','Security and authorization test']]
for row in trace: ws2.append(row)
for cell in ws2[1]: cell.font=Font(bold=True,color='FFFFFF'); cell.fill=PatternFill('solid',fgColor='1F6F53')
for col,w in enumerate([20,36,32,42],1): ws2.column_dimensions[get_column_letter(col)].width=w
for row in ws2.iter_rows():
    for c in row: c.alignment=Alignment(wrap_text=True,vertical='top')
wb.save(OUT/'Lab1_Requirements_Table.xlsx')

# Actors and use cases list
uc_doc=Document(); title_block(uc_doc,'Lab 1 — Actors and Use-Case Catalogue')
uc_doc.add_heading('Actors',level=1)
add_table(uc_doc,['Actor','Role in the system'],[
 ['Household Member','Enters activity data, views footprint results, sets targets, and records reduction actions.'],
 ['Household Administrator','Manages household membership, permissions, and shared household settings.'],
 ['Emission-Factor Provider','External data source that supplies or synchronizes versioned emission factors used in calculations.'],
 ['Notification / Export Service','External supporting service used only when the user requests a report export or notification.'],
],widths=[2.0,5.8],font_size=9)
uc_doc.add_heading('Use-case catalogue',level=1)
add_table(uc_doc,['ID','Use Case','Summary'],[
 ['UC-01','Manage Household Profile','Create or update household size, location, units, and member access.'],
 ['UC-02','Record Activity Data','Enter, validate, save, edit, or delete monthly electricity, fuel, transport, and waste data.'],
 ['UC-03','Calculate Footprint','Apply the selected emission-factor version to saved activity data and produce category and total kg CO2e.'],
 ['UC-04','Set Reduction Target','Choose a baseline, target percentage, target date, and optional target notes.'],
 ['UC-05','Track Progress','Compare actual emissions with the target and display variance, trend, and category contribution.'],
 ['UC-06','Log Reduction Action','Record an action such as reducing travel or improving energy efficiency and associate it with a period.'],
 ['UC-07','Export Footprint Report','Generate a readable summary for download or sharing when requested by an authorized user.'],
 ['UC-08','Synchronize Emission Factors','Retrieve, validate, and version emission-factor data from the external provider.'],
],widths=[0.7,2.2,4.9],font_size=8)
uc_doc.add_heading('Relationship decisions',level=1)
uc_doc.add_paragraph('UC-02 «include» Validate Activity Data because every saved activity record must pass validation. UC-03 «include» Apply Emission Factors because calculation cannot complete without that reusable behavior. UC-05 «include» Calculate Footprint because progress requires current actual emissions. UC-07 «extend» Share or Download Report because sharing is optional after a report is generated.')
save_doc(uc_doc,OUT/'Lab1_Actors_and_Use_Cases.docx')

# Mermaid diagram source
mmd='''flowchart LR\n    HM[Household Member]\n    HA[Household Administrator]\n    EFP[Emission-Factor Provider]\n    NES[Notification / Export Service]\n    subgraph SYS[Household Carbon Footprint & Target Tracker]\n      UC1((UC-01 Manage Household Profile))\n      UC2((UC-02 Record Activity Data))\n      V((Validate Activity Data))\n      UC3((UC-03 Calculate Footprint))\n      AF((Apply Emission Factors))\n      UC4((UC-04 Set Reduction Target))\n      UC5((UC-05 Track Progress))\n      UC6((UC-06 Log Reduction Action))\n      UC7((UC-07 Export Footprint Report))\n      SH((Share / Download Report))\n      UC8((UC-08 Synchronize Emission Factors))\n    end\n    HM --- UC1\n    HA --- UC1\n    HM --- UC2\n    HM --- UC4\n    HM --- UC5\n    HM --- UC6\n    HM --- UC7\n    EFP --- UC8\n    NES --- SH\n    UC2 -. 'include' .-> V\n    UC3 -. 'include' .-> AF\n    UC5 -. 'include' .-> UC3\n    UC7 -. 'extend' .-> SH\n    UC8 -. 'include' .-> AF\n'''
(OUT/'Lab1_Use_Case_Diagram.mmd').write_text(mmd,encoding='utf-8')

# ---------- Use-case flow document ----------
flow_doc=Document(); title_block(flow_doc,'Lab 1 — Use-Case Flow: UC-02 Record Activity Data')
flow_doc.add_heading('Use-case identification',level=1)
add_table(flow_doc,['Field','Specification'],[
 ['Use Case ID / Name','UC-02 — Record Activity Data'],
 ['Primary actor','Household Member'],
 ['Supporting actors','Household Administrator; Emission-Factor Provider (indirectly through stored factor configuration)'],
 ['Trigger','The household member chooses “Add activity data” for a selected month.'],
 ['Preconditions','The user is authenticated, has access to a household, and the selected household profile exists.'],
 ['Postconditions','A validated activity record is saved, the footprint is recalculated, and the dashboard reflects the new period value.'],
 ['Special relationship','UC-02 «include» Validate Activity Data; UC-03 is invoked after successful save.'],
],widths=[1.75,6.05],font_size=8)
flow_doc.add_heading('Main success scenario',level=1)
steps=[
 'The household member selects a household and chooses a month or reporting period.',
 'The system displays category fields for electricity, stationary fuel, transport, and waste, including value and unit controls.',
 'The household member enters one or more activity values and selects the unit for each value.',
 'The system validates that the period, category, numeric value, and unit are present and that values are non-negative.',
 'The system displays a review summary showing each entered activity item and its unit.',
 'The household member confirms “Save activity data.”',
 'The system stores the validated records and associates them with the household and reporting period.',
 'The system calculates category emissions using the active emission-factor version and sums the categories into a total kg CO2e value.',
 'The system displays a success message and updates the footprint dashboard, trend history, and target-progress indicators.',
 'The use case ends successfully.'
]
for i,s in enumerate(steps,1): flow_doc.add_paragraph(f'{i}. {s}')
flow_doc.add_heading('Alternate and exception flows',level=1)
flows=[
 ('4a. Invalid or incomplete input','The system highlights the offending field, explains the validation rule, and prevents saving. The household member corrects the value and returns to Step 4.'),
 ('4b. Unreasonable outlier confirmation','If the value is syntactically valid but outside the configured plausibility range, the system displays a warning and asks the user to confirm or edit it. On confirmation, processing continues at Step 5.'),
 ('7a. Save failure or temporary service interruption','The system does not create a partial record, displays a retry message, preserves the entered form data where possible, and allows the household member to retry or cancel.'),
 ('8a. Emission factor unavailable','The system marks the calculation as pending, explains that a factor is unavailable, and does not present the result as final. The user can retry synchronization or continue without losing the saved activity record.'),
]
for name,desc in flows:
    p=flow_doc.add_paragraph(); p.add_run(name+': ').bold=True; p.add_run(desc)
flow_doc.add_heading('Business rules and test notes',level=1)
add_bullets(flow_doc,[
 'All values are stored with their original unit and a normalized value used for calculation.',
 'A record cannot be saved without a reporting period, category, numeric value, and unit.',
 'The displayed total is the sum of displayed category results, rounded to two decimal places.',
 'Every recalculation records the emission-factor version so historical results remain auditable.'
])
save_doc(flow_doc,OUT/'Lab1_Use_Case_Flow.docx')

# Markdown flow for PDF export
flow_md=f'''# {TITLE}\n## Lab 1 — Use-Case Flow: UC-02 Record Activity Data\n\n**Primary actor:** Household Member  \n**Trigger:** The member chooses “Add activity data” for a selected month.  \n**Preconditions:** The user is authenticated and has access to a household.  \n**Postconditions:** Validated data is saved, the footprint is recalculated, and the dashboard is updated.\n\n### Main Success Scenario\n\n1. The member selects a household and reporting month.\n2. The system displays electricity, stationary-fuel, transport, and waste fields with value and unit controls.\n3. The member enters one or more values and selects each unit.\n4. The system validates period, category, numeric value, unit, and non-negative value rules.\n5. The system displays a review summary.\n6. The member confirms **Save activity data**.\n7. The system stores the validated records.\n8. The system applies the active emission factors and calculates category and total kg CO2e.\n9. The system updates the dashboard, trend history, and target-progress indicators.\n10. The use case ends successfully.\n\n### Alternate and Exception Flows\n\n**4a — Invalid or incomplete input.** The system highlights the field, explains the rule, prevents saving, and returns to validation after correction.\n\n**4b — Plausibility warning.** The system asks the member to confirm or edit an unusual but syntactically valid value before continuing.\n\n**7a — Save failure.** The system avoids a partial record, preserves form data where possible, and offers retry or cancel.\n\n**8a — Emission factor unavailable.** The record is saved as pending; the system does not present a final footprint until synchronization succeeds.\n\n### Business Rules\n\n- Values retain their original unit and a normalized calculation value.\n- The total equals the sum of displayed category values and is rounded to two decimal places.\n- Each result records the emission-factor version for auditability.\n'''
(OUT/'Lab1_Use_Case_Flow.md').write_text(flow_md,encoding='utf-8')

# ---------- Lab 2: student-friendly code and report ----------
# Reuse deterministic outputs from create_lab2_assets.py
key_data=json.loads((ROOT/'cipher_key.json').read_text())
subfreq=json.loads((ROOT/'substring_frequencies.json').read_text())
letter_data=json.loads((ROOT/'given_cipher_frequency.json').read_text())
solver=json.loads((ROOT/'solver_result.json').read_text())

student_script='''from pathlib import Path\nimport random\nimport string\nimport re\nfrom collections import Counter\n\n# Lab 2 solution for Household Carbon Footprint & Target Tracker\n# The script keeps punctuation, spaces, and line breaks unchanged.\nROOT = Path(__file__).parent\nINPUT = ROOT / "SRN.txt"\n\ndef generate_key(seed=20260825):\n    plain = list(string.ascii_lowercase)\n    cipher = plain.copy()\n    random.Random(seed).shuffle(cipher)\n    return dict(zip(plain, cipher))\n\ndef transform(text, mapping):\n    out=[]\n    for ch in text:\n        low=ch.lower()\n        if low in mapping:\n            value=mapping[low]\n            out.append(value.upper() if ch.isupper() else value)\n        else:\n            out.append(ch)\n    return ''.join(out)\n\ndef overlapping_frequency(text, pattern):\n    return len(re.findall(r"(?=" + re.escape(pattern) + r")", text))\n\nplaintext = INPUT.read_text(encoding="utf-8").lower()\nkey = generate_key()\nreverse = {v:k for k,v in key.items()}\nprint("Key mapping (plaintext -> ciphertext):")\nprint(", ".join(f"{a} -> {key[a]}" for a in string.ascii_lowercase))\nprint("\\nFrequencies:")\nfor item in ["th", "he", "ar", "ing", "e", "or"]:\n    print(f"{item}: {overlapping_frequency(plaintext, item)}")\n\nciphertext = transform(plaintext, key)\n(INPUT.parent / "SRN_ciphertext_student.txt").write_text(ciphertext, encoding="utf-8")\nrecovered = transform(ciphertext, reverse)\n(INPUT.parent / "SRN_decrypted_student.txt").write_text(recovered, encoding="utf-8")\nprint("\\nCiphertext and decrypted files written.")\n'''
(OUT/'lab2_cipher_solution.py').write_text(student_script,encoding='utf-8')

# Lab2 frequency Excel
wb2=Workbook(); ws=wb2.active; ws.title='Substring Frequencies'
ws.append(['Pattern','Frequency (overlapping)','Interpretation'])
for p in ['th','he','ar','ing','e','or']:
    ws.append([p,subfreq[p],'Counted case-insensitively with overlapping matches.'])
for c in ws[1]: c.font=Font(bold=True,color='FFFFFF'); c.fill=PatternFill('solid',fgColor='145D48')
for col,w in enumerate([20,25,65],1): ws.column_dimensions[get_column_letter(col)].width=w
ws3=wb2.create_sheet('Ciphertext Letter Frequency')
ws3.append(['Letter','Count','Percentage'])
for row in letter_data['table']: ws3.append([row['letter'],row['count'],row['percentage']/100])
for c in ws3[1]: c.font=Font(bold=True,color='FFFFFF'); c.fill=PatternFill('solid',fgColor='145D48')
for row in range(2,28): ws3.cell(row,3).number_format='0.00%'
for col,w in enumerate([12,14,18],1): ws3.column_dimensions[get_column_letter(col)].width=w
chart=BarChart(); chart.title='Supplied Ciphertext Letter Counts'; chart.y_axis.title='Count'; chart.x_axis.title='Ciphertext letter'
data=Reference(ws3,min_col=2,min_row=1,max_row=27); cats=Reference(ws3,min_col=1,min_row=2,max_row=27); chart.add_data(data,titles_from_data=True); chart.set_categories(cats); chart.height=8; chart.width=16; ws3.add_chart(chart,'E2')
ws4=wb2.create_sheet('English Benchmark')
benchmark={'e':12.02,'t':9.10,'a':8.12,'o':7.68,'i':7.31,'n':6.95,'s':6.28,'h':5.92,'r':6.02,'d':4.32,'l':3.98,'c':2.71,'u':2.88,'m':2.61,'w':2.09,'f':2.30,'g':2.03,'y':2.11,'p':1.82,'b':1.49,'v':1.11,'k':0.69,'j':0.10,'x':0.17,'q':0.11,'z':0.07}
ws4.append(['Letter','Supplied ciphertext %','Common English benchmark %','Difference (cipher - benchmark)'])
for ch in string.ascii_lowercase:
    pct=next(x['percentage'] for x in letter_data['table'] if x['letter']==ch)
    ws4.append([ch,pct/100,benchmark[ch]/100,pct/100-benchmark[ch]/100])
for c in ws4[1]: c.font=Font(bold=True,color='FFFFFF'); c.fill=PatternFill('solid',fgColor='145D48')
for r in range(2,28):
    for col in [2,3,4]: ws4.cell(r,col).number_format='0.00%'
for col,w in enumerate([12,25,28,30],1): ws4.column_dimensions[get_column_letter(col)].width=w
wb2.save(OUT/'Lab2_Frequency_Analysis.xlsx')

# Lab2 report docx
r=Document(); title_block(r,'Lab 2 — File Processing, Frequency Analysis, and Monoalphabetic Cipher')
r.add_heading('Student fields',level=1)
add_table(r,['Field','Value'],[['Name','____________________________'],['SRN','____________________________'],['Section','____________________________'],['Date',DATE]],widths=[1.5,6.3],font_size=9)
r.add_heading('Question 1 — Create and display SRN.txt',level=1)
r.add_paragraph('The required King Arthur passage is provided in the attached SRN.txt file. The file contains the handout text with stable ASCII apostrophe normalization for reproducible processing.')
r.add_heading('Question 2 — Lowercase conversion and requested frequencies',level=1)
r.add_paragraph('The analysis is case-insensitive and counts overlapping matches. For example, every character position is considered as a possible start of the requested pattern.')
add_table(r,['Pattern','Frequency'],[[p,subfreq[p]] for p in ['th','he','ar','ing','e','or']],widths=[2,2],font_size=9)
r.add_heading('Question 3 — Generated substitution key',level=1)
r.add_paragraph('A reproducible key was generated by shuffling the lowercase alphabet with random seed 20260825. The mapping below is plaintext → ciphertext; the reverse mapping is included in the JSON support file.')
map_rows=[[a,key_data['plaintext_to_ciphertext'][a]] for a in string.ascii_lowercase]
add_table(r,['Plaintext','Ciphertext'],map_rows,widths=[2,2],font_size=8)
r.add_heading('Question 4 — Ciphertext generation',level=1)
r.add_paragraph('The supplied Python script transforms letters through the generated key while preserving spaces, punctuation, and line breaks. The complete result is in SRN_ciphertext.txt.')
r.add_paragraph('Sample ciphertext for the second input passage:')
r.add_paragraph((ROOT/'sample_ciphertext.txt').read_text())
r.add_heading('Question 5 — Decryption',level=1)
r.add_paragraph('Decryption uses the inverse mapping. The recovered text in SRN_decrypted.txt matches the lowercase normalized plaintext character-for-character.')
r.add_heading('Question 6 — Comment on the sample ciphertext',level=1)
r.add_paragraph('The ciphertext preserves word boundaries, spacing, punctuation, and line breaks, which makes it readable as a sequence of word patterns but also leaks structural information. A monoalphabetic substitution keeps the same ciphertext symbol for every occurrence of a plaintext letter, so repeated letters, repeated words, and common short-word patterns remain visible. The sample is therefore suitable for demonstrating encryption and decryption, but it is not secure against frequency analysis or known-plaintext attacks.')
r.add_heading('Question 7 — Frequency analysis and decryption',level=1)
r.add_paragraph(f'The supplied ciphertext contains {letter_data["total_letters"]} alphabetic characters. The complete count-and-percentage table is in Lab2_Frequency_Analysis.xlsx and is reproduced below.')
freq_rows=[[x['letter'],x['count'],f"{x['percentage']:.2f}%"] for x in letter_data['table']]
add_table(r,['Letter','Count','Percentage'],freq_rows,widths=[1.4,1.4,1.8],font_size=7)
r.add_heading('Comparison with standard English frequencies',level=2)
r.add_paragraph('The comparison workbook uses Cornell University’s English-letter benchmark based on a sample of 40,000 words [1]. The supplied ciphertext is highly non-English in distribution because substitution permutes the underlying frequencies; the most common ciphertext symbols are therefore educated candidates for common plaintext letters, not direct identifications.')
r.add_paragraph('The most frequent ciphertext letters are t (58; 16.43%), w (44; 12.46%), n (30; 8.50%), x (24; 6.80%), e (23; 6.52%), and f/r (21 each; 5.95%). Repeated word patterns and single-letter words then constrain the guesses.')
r.add_heading('Recovered substitution mapping (ciphertext → plaintext)',level=2)
rev_rows=[[a,solver['mapping'][a]] for a in sorted(solver['mapping'])]
add_table(r,['Ciphertext','Plaintext'],rev_rows,widths=[2,2],font_size=8)
r.add_heading('Fully decrypted message',level=2)
r.add_paragraph(solver['plaintext'])
r.add_heading('Conclusion',level=1)
r.add_paragraph('The exercise demonstrates the complete workflow: create a file, normalize text, count overlapping patterns, generate a reproducible key, encrypt, decrypt, measure letter frequencies, exploit word patterns, and recover a monoalphabetic message. The results are deterministic and can be regenerated with the included scripts.')
r.add_heading('References',level=1)
r.add_paragraph('[1] Cornell University, “Frequency Table,” English Letter Frequency based on a sample of 40,000 words: https://pi.math.cornell.edu/~mec/2003-2004/cryptography/subs/frequencies.html')
save_doc(r,OUT/'Lab2_Submission_Report.docx')

# Lab 2 markdown report companion
report_md=f'''# {TITLE}\n## Lab 2 Submission Report\n\n**Domain:** {DOMAIN}  \n**Name:** ____________________  **SRN:** ____________________  **Section:** ____________________\n\n### Q2 frequencies\n\n| Pattern | Frequency |\n|---|---:|\n'''+''.join(f'| `{p}` | {subfreq[p]} |\n' for p in ['th','he','ar','ing','e','or'])+f'''\nThe counts are case-insensitive and overlapping.\n\n### Q3 key\n\nSeed: `20260825`. The complete mapping is in `cipher_key.json` and the student-friendly generator is `lab2_cipher_solution.py`.\n\n### Q6 comment\n\nThe sample ciphertext preserves spaces, punctuation, and line breaks. Because identical plaintext letters map to identical ciphertext letters, repeated patterns remain visible. The scheme is useful for teaching substitution but is not secure against frequency analysis.\n\n### Q7 frequency analysis\n\nThe supplied ciphertext contains **{letter_data['total_letters']}** alphabetic characters. See `Lab2_Frequency_Analysis.xlsx` for the full count/percentage table and English benchmark comparison. The benchmark is from Cornell University’s frequency table based on a sample of 40,000 words [1].\n\nRecovered ciphertext → plaintext mapping:\n\n`{', '.join(a+'→'+solver['mapping'][a] for a in sorted(solver['mapping']))}`\n\nDecrypted plaintext:\n\n> {solver['plaintext']}\n'''
(OUT/'Lab2_Submission_Report.md').write_text(report_md,encoding='utf-8')

# Submission README and manifest
readme=f'''# {TITLE} — Complete Lab Submission Package\n\n**Project domain:** {DOMAIN}  \n**Prepared by:** {AUTHOR}  \n**Date:** {DATE}\n\n## Submission checklist\n\n| Requirement | Delivered file | Status |\n|---|---|---|\n| Lab 1: exactly five FRs and two NFRs with IDs, descriptions, priority, measurable acceptance criteria, rationale, and comments | `Lab1_Requirements_Table.docx`; `Lab1_Requirements_Table.xlsx` | Complete |\n| Lab 1: actors and use cases | `Lab1_Actors_and_Use_Cases.docx` | Complete |\n| Lab 1: UML use-case diagram with boundary, actors, associations, and include/extend relationships | `Lab1_Use_Case_Diagram.pdf`; `Lab1_Use_Case_Diagram.png`; `Lab1_Use_Case_Diagram.mmd` | Complete |\n| Lab 1: one use-case flow with main success scenario and alternate flows | `Lab1_Use_Case_Flow.docx`; `Lab1_Use_Case_Flow.pdf`; `Lab1_Use_Case_Flow.md` | Complete |\n| Lab 2: SRN.txt source passage | `SRN.txt` | Complete |\n| Lab 2: requested substring frequencies | `substring_frequencies.json`; `Lab2_Frequency_Analysis.xlsx`; `Lab2_Submission_Report.docx` | Complete |\n| Lab 2: generated key and mapping | `cipher_key.json`; `lab2_cipher_solution.py`; `Lab2_Submission_Report.docx` | Complete |\n| Lab 2: ciphertext and decryption outputs | `SRN_ciphertext.txt`; `SRN_decrypted.txt`; `sample_ciphertext.txt`; `sample_decrypted.txt` | Complete |\n| Lab 2: Q7 frequency table, benchmark comparison, mapping, and full decryption | `Lab2_Frequency_Analysis.xlsx`; `Lab2_Submission_Report.docx` | Complete |\n\n## Personalization before submission\n\nReplace the blank Name, SRN, and Section fields in the Lab 2 report and add any instructor-specific date or section information. The project title and domain have already been applied throughout the package.\n\n## Reproducibility\n\nRun `python3 create_lab2_assets.py` to regenerate the raw Lab 2 outputs, then run `python3 build_submission.py` to rebuild the formatted deliverables. The cipher key is deterministic because the script uses seed `20260825`.\n'''
(OUT/'README.md').write_text(readme,encoding='utf-8')

# Copy raw support files into submission folder
for name in ['SRN.txt','SRN_ciphertext.txt','SRN_decrypted.txt','sample_input.txt','sample_ciphertext.txt','sample_decrypted.txt','substring_frequencies.json','cipher_key.json','given_ciphertext.txt','given_cipher_frequency.json','solver_result.json']:
    shutil.copy2(ROOT/name, OUT/name)

print('Built submission artifacts in', OUT)
''
