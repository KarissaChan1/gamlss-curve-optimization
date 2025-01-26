# Use R base image that includes Python
FROM r-base:4.3.2

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install required R packages
RUN R -e "install.packages(c('ggplot2', 'gamlss', 'dplyr'), repos='http://cran.rstudio.com/')"

WORKDIR /app

# Install poetry
RUN pip3 install poetry==1.8.3

# Copy project files
COPY README.md pyproject.toml poetry.lock* ./
COPY growth_curves ./growth_curves
COPY setup ./setup
COPY tests ./tests

# Configure matplotlib directory
ENV MPLCONFIGDIR=/tmp

# Configure poetry to create virtualenv in project
ENV POETRY_VIRTUALENVS_IN_PROJECT=true

# Install Python dependencies
RUN poetry install --no-interaction --no-ansi

# Set Python path
ENV PYTHONPATH=/app

# Set entrypoint and default command
ENTRYPOINT ["poetry", "run"]
CMD ["growth_curves", "-h"] 