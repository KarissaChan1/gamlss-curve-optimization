import os
import subprocess
import rpy2.robjects as ro
import pandas as pd
from rpy2.robjects import pandas2ri
from rpy2.robjects.packages import importr
from rpy2.robjects.vectors import ListVector
import argparse
import pickle
from growth_curves.generate_output_report import generate_output_report
import time
from datetime import timedelta
# Create age distribution plots by gender
import matplotlib.pyplot as plt
import numpy as np

# Activate pandas-to-R conversion
pandas2ri.activate()

def check_r_installed():
    """Check if R is installed and accessible."""
    try:
        subprocess.run(["R", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("R is installed.")
    except FileNotFoundError:
        raise RuntimeError("R is not installed. Run setup/install_r.py first.")

def run_r_script_from_file(script_path, **kwargs):
    """
    Runs an external R script using rpy2.

    Parameters:
    - script_path (str): Path to the R script file.
    - kwargs: Key-value arguments to pass into the R script as variables.

    Returns:
    - result: The result of the last evaluated R expression in the script.
    """
    try:
        # Pass Python variables to R environment
        for key, value in kwargs.items():
            ro.globalenv[key] = value

        # Load and run the R script
        with open(script_path, "r") as r_file:
            r_code = r_file.read()
        result = ro.r(r_code)
        return result
    except Exception as e:
        print(f"Error while running R script:\n{str(e)}")
        raise

def convert_r_object(r_obj):
    """
    Recursively converts R objects to Python-friendly formats.
    """
    if isinstance(r_obj, ro.vectors.ListVector):
        # Convert ListVector recursively
        return {k: convert_r_object(v) for k, v in r_obj.items()}
    elif isinstance(r_obj, ro.vectors.BoolVector):
        # Convert BoolVector (logical in R)
        return [None if x is ro.NA_Logical else bool(x) for x in r_obj]
    elif isinstance(r_obj, ro.vectors.FloatVector) or isinstance(r_obj, ro.vectors.IntVector):
        # Convert numeric/int vectors
        return [None if x is ro.NA_Real else x for x in r_obj]
    elif isinstance(r_obj, ro.rinterface.NULLType):
        # Convert R NULL to Python None
        return None
    elif hasattr(r_obj, "names"):  # Handle named vectors or data frames
        return {k: convert_r_object(v) for k, v in zip(r_obj.names, list(r_obj))}
    return r_obj

def compute_growth_curves(input_data, save_path, biomarkers, biomarker_tissue_map, tissue_types, sex_column, sex_labels, age_column, disease_data=None, disease_tissue_map=None, smoothing=None):
    """
    Compute growth curves for each combination of tissue type, sex, and biomarker.
    
    Parameters:
    - input_data: pandas DataFrame containing the input data
    - save_path: path to save results
    - biomarkers: list of full biomarker column names (e.g., ['GM_FA', 'WM_FA'])
    - biomarker_tissue_map: dictionary mapping biomarker columns to their tissue types
    - tissue_types: list of tissue types to analyze
    - sex_column: name of the sex column in input_data
    - sex_labels: list of unique sex labels
    - age_column: name of the age column
    - disease_data: pandas DataFrame containing disease patient data (optional)
    - disease_tissue_map: dictionary mapping disease biomarker columns to tissue types (optional)
    """
    # Path to the R script
    if smoothing:
        r_script_path = "./growth_curves/growth_curves_defaultsmoothing.R"
    else:
        r_script_path = "./growth_curves/growth_curves_selectmodels.R"

    results = {}
    # Get value counts of samples by gender
    gender_counts = input_data[sex_column].value_counts()
    print("\nSample counts by gender:")
    print(gender_counts)

    plt.figure(figsize=(10, 6))
    
    # Calculate bin edges based on all age data
    all_ages = input_data[age_column]
    bins = np.linspace(all_ages.min(), all_ages.max(), 30)
    
    # Plot histogram for each gender with alpha for transparency
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']  # Default matplotlib colors
    for i, gender in enumerate(sex_labels):
        gender_ages = input_data[input_data[sex_column] == gender][age_column]
        plt.hist(gender_ages, bins=bins, alpha=0.5, 
                label=f"{gender} (N={gender_counts[gender]})", 
                color=colors[i])

    plt.xlabel('Age')
    plt.ylabel('Frequency')
    plt.title('Age Distribution by Gender')
    plt.legend()
    
    # Save the plot
    plt.savefig(f"{save_path}/dataset_age_distribution.png")
    plt.close()
        
    for s in sex_labels:
        # Filter data for current sex
        filtered_input_data = input_data[input_data[sex_column] == s]
        
        # Filter disease data by sex if available and check if any data exists for this sex
        filtered_disease_data = None
        has_disease_data_for_sex = False
        if disease_data is not None:
            filtered_disease_data = disease_data[disease_data[sex_column] == s]
            has_disease_data_for_sex = len(filtered_disease_data) > 0
            print(f"has_disease_data_for_sex_{s}: {has_disease_data_for_sex}")

        for t in tissue_types:
            # Filter biomarkers for current tissue type
            tissue_biomarkers = [b for b in biomarkers if biomarker_tissue_map[b] == t]
            
            for biomarker in tissue_biomarkers:
                print(f"Processing {biomarker} for {s} sex...")
                model_params = {}
                r_input_data = ro.conversion.py2rpy(filtered_input_data)

                try:
                    # Only prepare and pass disease data if we have data for this sex
                    if has_disease_data_for_sex and disease_tissue_map is not None:
                        # Get corresponding disease biomarker columns for this tissue type
                        disease_cols = [col for col in disease_tissue_map.keys() 
                                     if biomarker.split('_')[-1] in col]
                        print(f"disease_cols: {disease_cols}")
                        
                        if disease_cols:
                            print(f"Found disease columns for {t}: {disease_cols}")  # Debug print
                            
                            # Create a list to store data for all matching columns
                            disease_data_list = []
                            
                            for disease_col in disease_cols:
                                try:
                                    disease_data_subset = pd.DataFrame({
                                        age_column: filtered_disease_data[age_column],
                                        biomarker: filtered_disease_data[disease_col],
                                        'tissue_column': disease_tissue_map[disease_col]
                                    }).dropna()
                                    
                                    if not disease_data_subset.empty:
                                        disease_data_list.append(disease_data_subset)
                                        print(f"Added data for {disease_col} with {len(disease_data_subset)} rows")
                                    else:
                                        print(f"No valid data for {disease_col} after removing NAs")
                                        
                                except Exception as e:
                                    print(f"Error processing {disease_col}: {str(e)}")
                                    continue

                            if disease_data_list:
                                print(f"Total disease data entries: {sum(len(df) for df in disease_data_list)}")
                            else:
                                print("No valid disease data collected")
                            
                            # Combine all disease data
                            if disease_data_list:
                                disease_data_for_r = pd.concat(disease_data_list, ignore_index=True)
                                disease_data_for_r = ro.conversion.py2rpy(disease_data_for_r)
                                
                                print(f"Prepared disease data for {t} with dimensions: {disease_data_for_r.nrow} rows x {disease_data_for_r.ncol} columns")  # Debug print
                                
                                result = run_r_script_from_file(
                                    r_script_path,
                                    input_data=r_input_data,
                                    column_x=age_column,
                                    column_y=biomarker,
                                    sex=s,
                                    disease_data=disease_data_for_r,
                                    tissue_column='tissue_column',
                                    save_path=save_path,
                                    tissue_type=t  # Add tissue type as parameter
                                )
                        else:
                            result = run_r_script_from_file(
                                r_script_path,
                                input_data=r_input_data,
                                column_x=age_column,
                                column_y=biomarker,
                                sex=s,
                                save_path=save_path
                            )
                    else:
                        result = run_r_script_from_file(
                            r_script_path,
                            input_data=r_input_data,
                            column_x=age_column,
                            column_y=biomarker,
                            sex=s,
                            save_path=save_path
                        )
                    
                    # Structure the results
                    if t not in results:
                        results[t] = {}
                    if s not in results[t]:
                        results[t][s] = {}
                    
                    model_params = {
                        "model_type": convert_r_object(result.rx2("model_type"))[0],
                        "aic": convert_r_object(result.rx2("aic")),
                        "mu": convert_r_object(result.rx2("mu")),
                        "sigma": convert_r_object(result.rx2("sigma")),
                        "nu": convert_r_object(result.rx2("nu")),
                        "tau": convert_r_object(result.rx2("tau")),
                        "coefs": convert_r_object(result.rx2("coefficients"))
                    }
                    
                    results[t][s][biomarker] = {
                        "model_parameters": model_params,
                        "centiles": pandas2ri.rpy2py(result.rx2("centile_data"))
                    }

                except Exception as e:
                    print(f"Error processing {biomarker} for {s} sex: {str(e)}")
                    continue

    # Save results
    pickle_file = os.path.join(save_path, "results.pkl")
    with open(pickle_file, "wb") as pkl_file:
        pickle.dump(results, pkl_file)

    print(f"Results saved to {pickle_file}")


def main():
    # Start timing
    start_time = time.time()

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input_path', required=True, dest='input_path',
                        help='Input spreadsheet path and filename')
    parser.add_argument('-a', '--age_col', required=True, dest='age_col',
                        help='Age column name')
    parser.add_argument('-t', '--tissue_types', nargs='+', required=False, dest='tissue_types',
                        help='Tissue types to plot (e.g., GM WM). If none specified, defaults to GM and WM')
    parser.add_argument('-d', '--disease_data', required=False, dest='disease_data',
                        help='Path to Excel file containing disease patient data')
    parser.add_argument('-b', '--biomarkers', nargs='+', required=True, dest='biomarker_types',
                        help='List of biomarker types to plot (e.g., FA MD). Will be combined with tissue types.')
    parser.add_argument('-g', '--group', nargs='+', required=False, dest='group',
                        help='Label of specific diagnostic groups of patients to plot, based on column "Cohort"')
    parser.add_argument('-sm', '--smoothing', required=False, dest='smoothing',
                        action='store_true',
                        help='Use default smoothing parameters in growth_curves.R instead of model optimizing script')
    parser.add_argument('-s', '--save_path', required=True, dest='save_path',
                        help='Path to save directory')

    args = parser.parse_args()
    input_path = args.input_path
    tissue_types = args.tissue_types if args.tissue_types else ['GM', 'WM']
    disease_data_path = args.disease_data
    age_col = args.age_col
    biomarker_types = args.biomarker_types
    save_path = args.save_path
    group = args.group
    smoothing = args.smoothing
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    # Input data from Python
    input_data = pd.read_excel(input_path)

    # if group is provided, filter input data for that group
    if group:
        if "Cohort" not in input_data.columns:
            raise ValueError('No column named "Cohort"')
        input_data = input_data[input_data["Cohort"].isin(group)]

    # Load disease data if provided
    disease_data = None
    if disease_data_path:
        disease_data = pd.read_excel(disease_data_path)
        print(f"disease_data: {disease_data}")

        # Verify biomarker columns exist in disease data
        disease_biomarkers = []
        for biomarker in biomarker_types:
            matching_cols = [col for col in disease_data.columns if col.endswith(f"_{biomarker}")]
            if not matching_cols:
                print(f"Warning: No columns found in disease data ending with '_{biomarker}'")
            disease_biomarkers.extend(matching_cols)
        print(f"disease_biomarkers: {disease_biomarkers}")
        
        if not disease_biomarkers:
            raise ValueError("No matching biomarker columns found in disease data")
        
        # Map disease tissue biomarkers to WM biomarkers
        disease_tissue_map = {}
        for disease_col in disease_biomarkers:
            biomarker = disease_col.split('_')[-1]  # Get biomarker name
            tissue = disease_col.split('_')[0]
            disease_tissue_map[disease_col] = tissue
        print(f"disease_tissue_map: {disease_tissue_map}")
    
    # Preprocess input data (ensure columns are there)
    sex_column = next((col for col in input_data.columns 
                      if "sex" in col.lower() or "gender" in col.lower()), None)
    if not sex_column:
        raise ValueError("No column found for sex/gender - check column names")

    # Generate all possible biomarker column names by combining tissue types and biomarker types
    biomarker_columns = []
    missing_columns = []
    biomarker_tissue_map = {}
    
    for tissue in tissue_types:
        for biomarker in biomarker_types:
            column_name = f"{tissue}_{biomarker}"
            if column_name in input_data.columns:
                biomarker_columns.append(column_name)
                biomarker_tissue_map[column_name] = tissue
            else:
                missing_columns.append(column_name)
    
    if not biomarker_columns:
        raise ValueError(
            f"None of the expected biomarker columns were found in the input data. "
            f"Missing columns: {missing_columns}"
        )
    elif missing_columns:
        print(f"Warning: The following expected columns were not found: {missing_columns}")
    
    input_data = input_data.dropna(subset=[sex_column] + biomarker_columns)
    unique_sex_labels = input_data[sex_column].unique()

    # check R installation before starting
    check_r_installed()

    # compute 
    compute_growth_curves(
        input_data, 
        save_path, 
        biomarker_columns, 
        biomarker_tissue_map, 
        tissue_types, 
        sex_column, 
        unique_sex_labels, 
        age_col, 
        disease_data if disease_data_path else None,
        disease_tissue_map if disease_data_path else None,
        smoothing
    )

    # Calculate and print runtime
    end_time = time.time()
    runtime = end_time - start_time
        
    generate_output_report(save_path, runtime, input_path, disease_data_path)

# Example Usage
if __name__ == "__main__":

    main()