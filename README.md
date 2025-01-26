# Tool for Generating GAMLSS Growth Curves
This tool replicates the GAMLSS growth curve construction in the following publication: [Developmental Curves of the Paediatric Brain Using FLAIR MRI Texture Biomarkers](https://journals.sagepub.com/doi/10.1177/08465371241262175) 

It is implemented using Python to run on command line, and uses rpy2 to run an R script for the gamlss package.
Normative growth curves (centiles 3, 15, 50, 85, 97) are plotted by sex, tissue, and biomarker, with an option to overlay diseased tissue data points onto the centile curves it a separate file of disease data is provided. 

## Requirements
- Ensure the biomarker sheets have columns for: Age, Sex, and biomarker columns with the naming convention "{object_type}_{biomarker}", e.g. WML_Median_Intensity
- Ensure the clinical colunns (e.g., Age, Sex) are cleaned. If there are missing data strings (e.g., "not available", "nan") rather than NaNs, the tool will output an error.

### Setup Instructions (do this before moving on to Usage step)
**Install R (versioni 4.4.2) and Required Packages**:
   Run the following command:
   ```
   cd gamlss-age-curves
   python setup/install_r.py
   ```
This checks for any existing R versions and installs R version 4.4.2 based on your operating system, along with required packages:
- ggplot2
- gamlss
- dplyr

### Usage
1. Install poetry: Visit the official poetry website (https://python-poetry.org/docs/) and follow the installation instructions for your operating system.
2. Clone the repo at: KarissaChan1/tiny-curvy-brains
3. run cd tiny-curvy-brains, enter the project directory.
4. Run poetry install, to set up all project dependencies within a dedicated virtual environment. Note: This project uses Poetry version 1.8.3.
5. Run poetry shell, activate the virtual environment.
6. View the help for usage:
```
usage: growth_curves [-h] -i INPUT_PATH -a AGE_COL
                     [-t TISSUE_TYPES [TISSUE_TYPES ...]]
                     [-d DISEASE_DATA]
                     [-g GROUP [GROUP ...]]
                     [-sm SMOOTHING]
                     -b BIOMARKERS [BIOMARKERS ...] -s SAVE_PATH

options:
  -h, --help            show this help message and exit
  -i INPUT_PATH, --input_path INPUT_PATH
                        Input spreadsheet path and filename
  -a AGE_COL, --age_col AGE_COL
                        Age column name (e.g., "Age_yrs_", "AGE", "Age", etc.)
  -t TISSUE_TYPES [TISSUE_TYPES ...], --tissue_types TISSUE_TYPES [TISSUE_TYPES ...]
                        Normative (non-disease)tissue types to plot (e.g., GM WM). If none specified, defaults to GM and WM
  -d DISEASE_DATA, --disease_data DISEASE_DATA
                        Path to Excel file containing disease patient data. Disease column names must have the same format as the biomarker column names (e.g., "tissuetype_biomarker") and biomarker names should match.
  -b BIOMARKERS [BIOMARKERS ...], --biomarkers BIOMARKERS [BIOMARKERS ...]
                        List of biomarker types to plot (e.g., Mean_Intensity). Will be combined with tissue types.
  -g GROUP [GROUP ...], --group GROUP [GROUP ...]
                        Label of specific diagnostic groups of patients to plot (e.g., CVD, VMCI, ADMCI, etc.), based on column "Cohort"
  -sm SMOOTHING, --smoothing SMOOTHING
                        Boolean flag for smoothing option for growth curves. Uses default smoothing parameters in growth_curves.R. If not specified, uses model optimizing script.
  -s SAVE_PATH, --save_path SAVE_PATH
                        Path to save directory

Example command:

To plot normative growth curves for Intensity, with disease tissue data overlaid:
```
growth_curves -i ./tests/data/HSC_Normals_Biomarkers_FINAL_cleaned.xlsx -a Age_yrs_ -b Intensity -s ./tests/test_output/ -d ./tests/data/HSC_Tumour_Biomarkers_FINAL_cleaned.xlsx
```

Example output plot:
![Female WM Intensity growth curve with NAWM overlaid](https://github.com/KarissaChan1/tiny-curvy-brains/blob/main/readme_pics/centile_plot_WM_F_Intensity_disease%20copy.png?raw=true)

### Docker Usage
### Prerequisites
- Docker Desktop must be installed and running on your system
  - For Windows/Mac: Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
  - For Linux: Install [Docker Engine](https://docs.docker.com/engine/install/)

### Building the Docker Image
You can build the Docker image using the provided Makefile:
```bash
make build
```

### Running with Docker
The Docker container can be run using either the Makefile or direct Docker commands.

Using Makefile (runs with example parameters):
```bash
make run
```

Using Docker directly:
```bash
docker run --rm \
    -v /path/to/your/data:/app/data \
    -v /path/to/output:/app/output \
    karissachan1/tiny-curvy-brains:latest \
    growth_curves \
    -i /app/data/your_input_file.xlsx \
    -a Age_yrs_ \
    -b YourBiomarker \
    -s /app/output
```
