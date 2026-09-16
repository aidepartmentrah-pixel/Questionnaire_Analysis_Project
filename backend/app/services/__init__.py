"""Business-logic services (CSV parsing, profiling, preprocessing, training, export).

Route handlers stay thin and delegate to services here; no ML or data-wrangling
logic should live directly in app/api/routes.
"""
