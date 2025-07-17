"""
TradeByte Sub-Account Management System

This module provides sub-account management functionality including:
- Account creation, deletion, and editing
- Fund transfers between accounts
- Trade posting and history tracking
- Real-time portfolio valuation
- GUI interface for account management
"""

from .account import SubAccount, AccountEdit
from .ui import SubAccountUI

__all__ = ['SubAccount', 'AccountEdit', 'SubAccountUI']

# Version info
__version__ = '1.0.0'
__author__ = 'TradeByte Team' 