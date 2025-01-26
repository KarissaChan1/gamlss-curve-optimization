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
  # Apply log transformation
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
# z_scores_x <- scale(subset_data[[column_x]])
# z_scores_y <- scale(subset_data[[column_y]])

# # Remove rows where either column has z-score > 3 or < -3 (outliers)
# subset_data <- subset_data[abs(z_scores_x) <= 3 & abs(z_scores_y) <= 3, ]

subset_data <- subset_data[subset_data[[column_y]] < quantile(subset_data[[column_y]], 0.99), ]

# Check if there are any rows left after outlier removal
if (nrow(subset_data) == 0) {
  stop("Error: No valid data after removing outliers.")
}

print(paste("Number of rows after outlier removal:", nrow(subset_data)))

# Assign cleaned data back to input_data for model fitting
input_data <- subset_data

# Set lambda and n.cyc based on dataset size
# if (nrow(input_data) > 500) {
#   lambda <- 500
#   n.cyc <- 500
# } else {
#   lambda <- NULL
#   n.cyc <- 100
# }

# print(paste("Using lambda =", lambda, "and n.cyc =", n.cyc))

lambda <- 3000

#GAMLSS MODELS
# Dynamic formula setup
if (is.null(lambda)) {
  dynamic_formula <- as.formula(paste(column_y, "~ pb(", column_x, ")"))
  sigma_formula <- as.formula(paste("~ pb(", column_x, ")"))
} else {
  dynamic_formula <- as.formula(paste(column_y, "~ pb(", column_x, ", lambda =", lambda, ")"))
  sigma_formula <- as.formula(paste("~ pb(", column_x, ", lambda =", lambda, ")"))
}

# Print constructed formulas for debugging
print(dynamic_formula)
print(sigma_formula)

# Fit the gamlss models
BCT_model <- tryCatch({
  gamlss(
    formula = dynamic_formula,
    sigma.formula = sigma_formula,
    nu.formula = ~ 1,
    tau.formula = ~ 1,
    family = BCT,
    data = input_data,
    control = gamlss.control(c.crit=0.001, trace = TRUE),
    weights = input_data$weights
  )
}, error = function(e) NULL)

BCCG_model <- tryCatch({
  gamlss(
    formula = dynamic_formula,
    sigma.formula = sigma_formula,
    nu.formula = ~ 1,
    tau.formula = ~ 1,
    family = BCCG,
    data = input_data,
    control = gamlss.control(c.crit=0.001, trace = TRUE)
  )
}, error = function(e) NULL)

BCPE_model <- tryCatch({
  gamlss(
    formula = dynamic_formula,
    sigma.formula = sigma_formula,
    nu.formula = ~ 1,
    tau.formula = ~ 1,
    family = BCPE,
    data = input_data,
    control = gamlss.control(c.crit=0.001, trace = TRUE)
  )
}, error = function(e) NULL)

NO_model <- tryCatch({
  gamlss(
    formula = dynamic_formula,
    sigma.formula = sigma_formula,
    nu.formula = ~ 1,
    tau.formula = ~ 1,
    family = NO,
    data = input_data,
    control = gamlss.control(c.crit=0.001, trace = TRUE)
  )
}, error = function(e) NULL)

# Calculate AIC only for successfully fitted models
models_list <- list(BCT_model, BCCG_model, BCPE_model, NO_model)
valid_models <- models_list[!sapply(models_list, is.null)]

if (length(valid_models) == 0) {
  stop("Error: None of the models could be fitted successfully.")
}

# Calculate AIC for each valid model individually
aic_values <- sapply(valid_models, AIC)
model_names <- c("BCT_model", "BCCG_model", "BCPE_model", "NO_model")[!sapply(models_list, is.null)]
names(aic_values) <- model_names

# Find the best model
best_model_name <- names(which.min(aic_values))
best_model_object <- valid_models[[which.min(aic_values)]]
aic <- min(aic_values)

# Plot and save residuals
residuals_file <- paste0(save_path, "/residuals_", sex,"_",column_y, ".png")
png(filename = residuals_file,
    width = 3000, 
    height = 2400,
    res = 300
)

# Create residual plot using plot.gamlss
plot(best_model_object, 
     xvar=input_data[[column_x]], 
     parameters=1,
     summaries=paste("Residuals of", column_y, ": ", sex))

dev.off()
print(paste("Residuals plot saved as:", residuals_file))


# COMPUTE NORMATIVE CENTILES
output_file <- paste0(save_path, "/centile_plot_", sex,"_",column_y, ".png")
png(filename = output_file, 
    width = 3000,
    height = 2400,
    res = 300
)

# Plot the centiles
centile_data <- centiles(
  best_model_object, 
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
print(paste("Centile plot saved as:", output_file))

# Plot disease data only for WM tissue type
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
        best_model_object, 
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

## get results to return
# Convert centiles to a data frame
centile_df <- as.data.frame(centile_data)

# Extract coefficients (always available)
coefficients_values <- coef(best_model_object)

mu_values <- if ("mu" %in% names(best_model_object$parameters)) {
  if (all(is.na(fitted(best_model_object, what = "mu")))) {
    "NA"
  } else {
    as.numeric(fitted(best_model_object, what = "mu"))
  }
} else {
  "Not Applicable"
}

sigma_values <- if ("sigma" %in% names(best_model_object$parameters)) {
  if (all(is.na(fitted(best_model_object, what = "sigma")))) {
    "NA"
  } else {
    as.numeric(fitted(best_model_object, what = "sigma"))
  }
} else {
  "Not Applicable"
}

nu_values <- if ("nu" %in% names(best_model_object$parameters)) {
  if (all(is.na(fitted(best_model_object, what = "nu")))) {
    "NA"
  } else {
    as.numeric(fitted(best_model_object, what = "nu"))
  }
} else {
  "Not Applicable"
}

tau_values <- if ("tau" %in% names(best_model_object$parameters)) {
  if (all(is.na(fitted(best_model_object, what = "tau")))) {
    "NA"
  } else {
    as.numeric(fitted(best_model_object, what = "tau"))
  }
} else {
  "Not Applicable"
}

# Return parameters to Python
result_list <- list(
    model_type = unname(as.character(best_model_name)[1]),
    aic = as.numeric(aic),
    mu = mu_values,
    sigma = sigma_values,
    nu = nu_values,
    tau = tau_values,
    coefficients = as.list(coefficients_values),
    centile_data = centile_df
)

result_list