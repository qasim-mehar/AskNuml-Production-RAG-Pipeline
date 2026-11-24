"""Integration campaign: real adapters composed at the service level (L3, L12).

This package is the integration lane's wiring. It never replaces the core fakes:
those remain the CI default, and the real adapters are selected only through the
typed settings (L8).
"""
