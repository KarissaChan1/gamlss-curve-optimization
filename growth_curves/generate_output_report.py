import os
import pandas as pd
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from datetime import datetime
import pickle

def generate_output_report(results_folder, run_time, input_file, disease_tissue=None):
    '''
    working_path: output path
    results_folder: folder containing results pickle file
    run_time: run time of the model fitting
    input_file: path to input spreadsheet
    '''
    print('Generating output report...')

    # Load results from pickle file
    with open(os.path.join(results_folder, 'results.pkl'), 'rb') as f:
        results = pickle.load(f)
    print(results)

    # Get Run time
    hours, remainder = divmod(run_time, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Format the run time as X h X min X s
    formatted_run_time = f"{int(hours)} h {int(minutes)} min {int(seconds)} s"

    # Create a PDF using SimpleDocTemplate
    pdf = SimpleDocTemplate(os.path.join(results_folder, 'growth_curves_output_report.pdf'), pagesize=letter)
    
    styles = getSampleStyleSheet()
    figure_caption_style = ParagraphStyle(
    'CenteredStyle', 
    parent=styles['Italic'],
    alignment=TA_CENTER
    )
    content = []

    title = Paragraph("GAMLSS Age Curves Report", styles['Title'])
    content.append(title)

    description_text = (
        f"This is the output report for fitted GAMLSS models ran on: {datetime.now()} <br/><br/>"
        f"Dataset filename: {os.path.basename(input_file)} <br/>"
    )
    if disease_tissue is not None:
        description_text += f"Disease data filename: {os.path.basename(disease_tissue)} <br/>"
    description_text += f"Run time: {formatted_run_time}  <br/><br/>"
    
    description = Paragraph(description_text, styles['BodyText'])
    content.append(description)
    analysis_desc = Paragraph(
        "This analysis uses Generalized Additive Models for Location, Scale and Shape (GAMLSS) in R "
        "to construct normative age curves for FLAIR biomarkers. The data is stratified by sex and tissue type, "
        "and models are optimized to characterize the relationship between age and each biomarker. "
        "The models account for changes in both the mean trend and the spread of values across age. "
        "Centile curves (3rd, 15th, 50th, 85th, and 97th percentiles) are generated to show the expected distribution of values at each age.<br/><br/>", 
        styles['BodyText'])
    content.append(analysis_desc)
    

    # Add age distribution plot
    age_dist_path = os.path.join(results_folder, 'dataset_age_distribution.png')
    if os.path.exists(age_dist_path):
        content.append(Spacer(1, 12))
        content.append(Image(age_dist_path, width=6*inch, height=4*inch))
        content.append(Spacer(1, 6))
        
        age_dist_caption = Paragraph(
            "Age distribution between genders in the dataset analyzed for age curves.", 
            figure_caption_style
        )
        content.append(age_dist_caption)
        content.append(Spacer(1, 12))
    
    # Add Model Parameters section
    content.append(PageBreak())
    heading = Paragraph("Modelling Results", styles['Heading2'])
    content.append(heading)

    # Get all unique biomarkers and genders
    biomarkers = set()
    genders = set()
    for tissue in results:
        genders.update(results.get(tissue, {}).keys())
        for gender in results.get(tissue, {}):
            biomarkers.update(results.get(tissue, {}).get(gender, {}).keys())

    # Loop through tissues first, then biomarkers
    for tissue in results.keys():
        tissue_heading = Paragraph(f"Age Curves for Tissue Type: {tissue}", styles['Heading3'])
        content.append(tissue_heading)
        content.append(Spacer(1, 6))

        # Get tissue data safely
        tissue_data = results.get(tissue, {})
        gender_data = {gender: tissue_data.get(gender, {}) for gender in genders}

        for biomarker in biomarkers:
            # Skip if biomarker not present for this tissue in any gender
            if not any(biomarker in gender_data[gender] for gender in genders):
                continue

            biomarker_heading = Paragraph(f"Biomarker: {biomarker}", styles['Heading4'])
            content.append(biomarker_heading)
            content.append(Spacer(1, 12))

            # First add parameter table
            table_caption = Paragraph(
                f"{biomarker} Optimized Model Parameters by Sex",
                figure_caption_style
            )
            content.append(table_caption)
            content.append(Spacer(1, 6))
            
            # Create table data with columns for each gender
            header = ['Parameter'] + [f'Value ({gender})' for gender in sorted(genders)]
            data = [header]  # Header row
            
            # Get parameters for all genders safely
            params = {
                gender: gender_data[gender].get(biomarker, {}).get('model_parameters') 
                if biomarker in gender_data[gender] else None 
                for gender in genders
            }

            # Add best model family and AIC first
            model_row = ['Best model family']
            aic_row = ['AIC']
            for gender in sorted(genders):
                if params[gender]:
                    model_row.append(str(params[gender].get('model_type', 'N/A')))
                    aic_row.append('N/A' if params[gender].get('aic') is None else f"{float(params[gender]['aic']):.2f}")
                else:
                    model_row.append('N/A')
                    aic_row.append('N/A')
            data.append(model_row)
            data.append(aic_row)

            # Get all unique parameter names
            param_names = set()
            for gender_params in params.values():
                if gender_params:
                    param_names.update(gender_params['coefs'].keys())

            # Add coefficients
            for param_name in sorted(param_names):
                row = [str(param_name)]
                for gender in sorted(genders):
                    if params[gender] and param_name in params[gender]['coefs']:
                        row.append(f"{float(params[gender]['coefs'][param_name][0]):.6f}")
                    else:
                        row.append("N/A")
                data.append(row)

            # Add distribution parameters if applicable
            for param in ['mu', 'sigma', 'nu', 'tau']:
                row = [param]
                for gender in sorted(genders):
                    if params[gender] and param in params[gender] and params[gender][param] is not None:
                        row.append(str(params[gender][param][0]))
                    else:
                        row.append("N/A")
                data.append(row)

            # Create and style table
            param_table = Table(data)
            param_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
                
            content.append(param_table)
            content.append(Spacer(1, 12))

            # Check for existence of growth curves for each gender
            figure_images = []
            has_figures = False
            for gender in sorted(genders):
                # Try disease plot first if disease_tissue is not None
                if disease_tissue is not None:
                    img_path = os.path.join(results_folder, f"centile_plot_{gender}_{biomarker}_disease.png")
                    if not os.path.exists(img_path):
                        # If disease plot doesn't exist, try regular plot
                        img_path = os.path.join(results_folder, f"centile_plot_{gender}_{biomarker}.png")
                else:
                    img_path = os.path.join(results_folder, f"centile_plot_{gender}_{biomarker}.png")

                if os.path.exists(img_path):
                    img = Image(img_path, width=3*inch, height=3*inch)
                    figure_images.append(img)
                    has_figures = True
                else:
                    figure_images.append(Paragraph(f"No growth curve available for {gender}", styles['Normal']))

            # Only add figure table and caption if at least one figure exists
            if has_figures:
                figure_table = Table([figure_images])  # Now a single row with all gender figures
                figure_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ]))

                # Modify caption based on whether it's a disease tissue
                caption_text = f"Normative {biomarker.split('_', 1)[1]} age curves for female (left) and male (right) in {tissue}"
                if disease_tissue is not None:
                    caption_text += " (Disease Tissue)"
                
                figure_caption = Paragraph(caption_text, figure_caption_style)
                
                content.append(figure_table)
                content.append(Spacer(1, 6))
                content.append(figure_caption)
                content.append(Spacer(1, 12))

            # Add page break after each biomarker
            content.append(PageBreak())

            # Add residuals plots in a table
            residuals_images = []
            has_residuals = False
            for gender in sorted(genders):
                residuals_path = os.path.join(results_folder, f"residuals_{gender}_{biomarker}.png")
                if os.path.exists(residuals_path):
                    residuals_img = Image(residuals_path, width=3*inch, height=3*inch)
                    residuals_images.append(residuals_img)
                    has_residuals = True
                else:
                    residuals_images.append(Paragraph(f"No residuals plot available for {gender}", styles['Normal']))

            if has_residuals:
                residuals_table = Table([residuals_images])
                residuals_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ]))

                residuals_caption = Paragraph(f"Residuals of female (left) and male (right) {biomarker.split('_', 1)[1]} age curves in {tissue}", figure_caption_style)
                
                content.append(residuals_table)
                content.append(Spacer(1, 6))
                content.append(residuals_caption)
                content.append(Spacer(1, 12))

    # Build the PDF document
    pdf.build(content)