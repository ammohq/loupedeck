"""
Test script to verify that the pyloupe package can be installed and imported correctly.
"""

try:
    import pyloupe
    print(f"Successfully imported pyloupe version {pyloupe.__version__}")
    
    # Test importing some key classes
    from pyloupe import LoupedeckDevice, discover, HAPTIC
    print("Successfully imported key classes and functions")
    
    print("All tests passed!")
except ImportError as e:
    print(f"Error importing pyloupe: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")