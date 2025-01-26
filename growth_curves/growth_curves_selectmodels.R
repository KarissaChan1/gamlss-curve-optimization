# Function to check and install required packages
check_and_install <- function(pkg) {
  if (!require(pkg, character.only = TRUE)) {
    install.packages(pkg, repos = "http://cran.r-project.org")
    library(pkg, character.only = TRUE)
  }
}

# List of required packages
required_packages <- c("ggplot2", "gamlss", "dplyr", "readr", "data.table")

# Check and install each package
for (pkg in required_packages) {
  check_and_install(pkg)
}

# Print a message to confirm packages are loaded
print("All required R packages are installed and loaded.")

# run script
print("Running R script...")

library(ggplot2)
library(dplyr)
library(readr)

# Check if input_data exists
if (!exists("input_data")) {
  stop("Error: input_data is missing!")
}

# Ensure necessary columns exist
if (!(column_x %in% colnames(input_data)) || !(column_y %in% colnames(input_data))) {
  stop("Error: Specified columns are not present in the input data!")
}

# Check for disease data
has_disease_data <- exists("disease_data") && !is.null(disease_data)
print(paste("has_disease_data:", has_disease_data))

# Check for tissue column if disease data exists
if (has_disease_data && !("tissue_column" %in% colnames(disease_data))) {
  stop("Error: tissue_column is required in disease data!")
}

# Subset data to only include required columns
required_cols <- c(column_x, column_y)
subset_data <- input_data[, required_cols]

# Remove rows with any NA values
subset_data <- na.omit(subset_data)

# Calculate z-scores for both columns
z_scores_x <- scale(subset_data[[column_x]])
z_scores_y <- scale(subset_data[[column_y]])

# Remove rows where either column has z-score > 3 or < -3 (outliers)
subset_data <- subset_data[abs(z_scores_x) <= 3 & abs(z_scores_y) <= 3, ]

# Check if there are any rows left after outlier removal
if (nrow(subset_data) == 0) {
  stop("Error: No valid data after removing outliers.")
}

print(paste("Number of rows after outlier removal:", nrow(subset_data)))

# Analyze distribution and check if log transformation is needed
skewness_y <- mean((subset_data[[column_y]] - mean(subset_data[[column_y]]))^3) / 
              sd(subset_data[[column_y]])^3
kurtosis_y <- mean((subset_data[[column_y]] - mean(subset_data[[column_y]]))^4) / 
              sd(subset_data[[column_y]])^4 - 3

print(paste("Skewness of", column_y, ":", round(skewness_y, 3)))
print(paste("Kurtosis of", column_y, ":", round(kurtosis_y, 3)))

# Check if log transformation might be beneficial
# High positive skewness (> 1) and all positive values suggest log transform might help
should_log_transform <- skewness_y > 1 && all(subset_data[[column_y]] > 0)

if (should_log_transform) {
  print(paste("Log transformation recommended for", column_y))
  subset_data[[column_y]] <- log(subset_data[[column_y]])
  print("Log transformation applied")
  
  # Recalculate skewness and kurtosis after transformation
  skewness_y_after <- mean((subset_data[[column_y]] - mean(subset_data[[column_y]]))^3) / 
                      sd(subset_data[[column_y]])^3
  print(paste("Skewness after log transform:", round(skewness_y_after, 3)))
} else {
  print("No log transformation needed based on distribution")
}

# # Calculate z-scores for both columns
z_scores_x <- scale(subset_data[[column_x]])
z_scores_y <- scale(subset_data[[column_y]])

# Remove rows where either column has z-score > 3 or < -3 (outliers)
subset_data <- subset_data[abs(z_scores_x) <= 3 & abs(z_scores_y) <= 3, ]

# Assign cleaned data back to input_data for model fitting
input_data <- subset_data


# Define smoothing methods
smoothing_methods <- list(
  "pb" = function(x) paste0("pb(", x, ")"),
  "cs" = function(x) paste0("cs(", x, ")"),
  "lo" = function(x) paste0("lo(", x, ")")
)

# Define GAMLSS families
gamlss_families <- list("BCT", "BCCG", "BCPE", "NO", "GA", "IG", "WEI")

# Function to find optimal parameters for each smoothing method
find_optimal_parameters <- function(model_formula, data, family, smooth_method) {
  min_lambda <- 5000
  lambda_range <- seq(min_lambda, 10000, by = 1000)
  df_range <- seq(1, 4, by = 1)
  
  best_aic <- Inf
  optimal_params <- list(lambda = min_lambda, df = 4)
  
  for(lambda in lambda_range) {
    for(df in df_range) {
      formula_str <- switch(smooth_method,
        "pb" = paste0("pb(", column_x, ", lambda=", lambda, ", df=", df, ")"),
        "cs" = paste0("cs(", column_x, ", lambda=", lambda, ", df=", df, ")"),
        "lo" = paste0("lo(", column_x, ", span=", df/nrow(data), ")")
      )
      
      temp_model <- try(gamlss(
        formula = as.formula(paste(column_y, "~", formula_str)),
        sigma.formula = as.formula(paste("~", formula_str)),
        nu.formula = ~ 1,
        tau.formula = ~ 1,
        family = as.name(family),
        data = data,
        control = gamlss.control(c.crit=0.001, trace = FALSE)
      ), silent = TRUE)
      
      if(!inherits(temp_model, "try-error")) {
        current_aic <- AIC(temp_model)
        if(current_aic < best_aic) {
          best_aic <- current_aic
          optimal_params <- list(lambda = lambda, df = df)
        }
      }
    }
  }
  
  return(optimal_params)
}

# Initialize variables for best model
best_model <- NULL
best_aic <- Inf
best_smoothing <- NULL
best_family <- NULL
best_params <- NULL

print("Starting model selection process...")

# Iterate over smoothing methods and GAMLSS families
for (smooth_name in names(smoothing_methods)) {
  for (family in gamlss_families) {
    print(paste("Trying", smooth_name, "smoothing with", family, "family"))
    
    # Find optimal parameters for this combination
    params <- find_optimal_parameters(
      model_formula = as.formula(paste(column_y, "~", smoothing_methods[[smooth_name]](column_x))),
      data = input_data,
      family = family,
      smooth_method = smooth_name
    )
    
    # Construct formula with optimal parameters
    formula_str <- switch(smooth_name,
      "pb" = paste0("pb(", column_x, ", lambda=", params$lambda, ", df=", params$df, ")"),
      "cs" = paste0("cs(", column_x, ", lambda=", params$lambda, ", df=", params$df, ")"),
      "lo" = paste0("lo(", column_x, ", span=", params$df/nrow(input_data), ")")
    )
    
    # Fit model with optimal parameters
    current_model <- tryCatch({
      gamlss(
        formula = as.formula(paste(column_y, "~", formula_str)),
        sigma.formula = as.formula(paste("~", formula_str)),
        nu.formula = ~ 1,
        tau.formula = ~ 1,
        family = as.name(family),
        data = input_data,
        control = gamlss.control(c.crit = 0.001, trace = FALSE)
      )
    }, error = function(e) NULL)
    
    if (!is.null(current_model)) {
      current_aic <- AIC(current_model)
      if (current_aic < best_aic) {
        best_model <- current_model
        best_aic <- current_aic
        best_smoothing <- smooth_name
        best_family <- family
        best_params <- params
      }
    }
  }
}

print(paste("Best model:", best_family, "family with", best_smoothing, "smoothing"))
print(paste("Best AIC:", round(best_aic, 2)))
print(paste("Optimal parameters: lambda =", best_params$lambda, ", df =", best_params$df))

# Create summary string
summary_text <- paste0(
    "\nBest Model Summary:\n",
    "-------------------\n",
    "Family: ", best_family, "\n",
    "Smoothing Method: ", best_smoothing, "\n",
    "AIC: ", round(best_aic, 2), "\n",
    "Lambda: ", best_params$lambda, "\n",
    "Degrees of Freedom: ", best_params$df, "\n",
    "-------------------\n"
)

# Print the summary
cat(summary_text)

# Plot and save residuals using best model
residuals_file <- paste0(save_path, "/residuals_", sex,"_",column_y, ".png")
png(filename = residuals_file,
    width = 3000, 
    height = 2400,
    res = 300
)
plot(best_model, 
     xvar=input_data[[column_x]], 
     parameters=1,
     summaries=paste("Residuals of", column_y, ": ", sex))
dev.off()

# Compute and plot centiles using best model
output_file <- paste0(save_path, "/centile_plot_", sex,"_",column_y, ".png")
png(filename = output_file, 
    width = 3000,
    height = 2400,
    res = 300
)

centile_data <- centiles(
  best_model, 
  xvar = input_data[[column_x]], 
  xlab = column_x, 
  ylab = column_y, 
  main=paste("Centiles of", column_y, ": ", sex),
  cent = c(3, 15, 50, 85, 97), 
  col.centiles = c("grey", "black", "red", "black", "grey"),
  legend = FALSE,
  ylim = range(input_data[[column_y]]),
  save=TRUE
)
dev.off()

# Handle disease data plotting (if applicable)
if (has_disease_data && exists("tissue_type") && tissue_type == "WM") {
    print(paste("Processing disease data for", tissue_type, "tissue type"))  # Debug print
    print(paste("Number of disease data points:", nrow(disease_data)))  # Debug print
    
    output_file_disease <- paste0(save_path, "/centile_plot_", sex,"_",column_y, "_disease.png")
    png(filename = output_file_disease, 
        width = 3000,
        height = 2400,
        res = 300
    )
    
    # Plot the centiles first
    centiles(
        best_model, 
        xvar = input_data[[column_x]], 
        xlab = column_x, 
        ylab = column_y, 
        main=paste("Centiles of", column_y, ": ", sex, " with Disease Data"),
        cent = c(3, 15, 50, 85, 97), 
        col.centiles = c("grey", "black", "red", "black", "grey"),
        legend = FALSE,
        ylim = range(c(input_data[[column_y]], disease_data[[column_y]]))
    )
    
    # Plot all disease points (no tissue filtering needed - already done in Python)
    points(
        x = disease_data[[column_x]],
        y = disease_data[[column_y]],
        col = "blue",
        pch = 21,
        bg = "blue",
        cex = 1.2
    )
    
    # Add tissue labels
    text(
        x = disease_data[[column_x]] + max(disease_data[[column_x]]) * 0.02,
        y = disease_data[[column_y]],
        labels = disease_data$tissue_column,
        pos = 4,
        cex = 0.8,
        col = "blue"
    )
    
    # Add legend for unique tissue types
    legend("topright", 
           legend = unique(disease_data$tissue_column),
           col = "blue",
           pch = 21,
           pt.bg = "blue",
           cex = 0.8,
           title = "Disease Types")
    
    dev.off()
    print(paste("Disease plot saved for", tissue_type, "tissue type"))
}

# Prepare results to return to Python
result_list <- list(
    model_type = unname(as.character(best_family)[1]),
    smoothing_method = best_smoothing,
    optimal_lambda = best_params$lambda,
    optimal_df = best_params$df,
    aic = as.numeric(best_aic),
    mu = fitted(best_model, what = "mu"),
    sigma = fitted(best_model, what = "sigma"),
    nu = if ("nu" %in% names(best_model$parameters)) fitted(best_model, what = "nu") else NULL,
    tau = if ("tau" %in% names(best_model$parameters)) fitted(best_model, what = "tau") else NULL,
    coefficients = as.list(coef(best_model)),
    centile_data = as.data.frame(centile_data),
    summary = summary_text
)

result_list