#!/bin/bash

# Simple Calculator Script

echo "Welcome to the Calculator!"

# Get first number
read -p "Enter the first number: " num1

# Get second number
read -p "Enter the second number: " num2

# Show menu of operations
echo "Choose an operation:"
echo "1. Addition (+)"
echo "2. Subtraction (-)"
echo "3. Multiplication (*)"
echo "4. Division (/)"

read -p "Enter your choice (1/2/3/4): " choice

# Perform calculation based on user choice
case $choice in
    1)
        result=$((num1 + num2))
        echo "Result: $num1 + $num2 = $result"
        ;;
    2)
        result=$((num1 - num2))
        echo "Result: $num1 - $num2 = $result"
        ;;
    3)
        result=$((num1 * num2))
        echo "Result: $num1 * $num2 = $result"
        ;;
    4)
        # Check if dividing by zero
        if [ "$num2" -eq 0 ]; then
            echo "Error: Division by zero is not allowed!"
        else
            result=$(echo "scale=2; $num1 / $num2" | bc)
            echo "Result: $num1 / $num2 = $result"
        fi
        ;;
    *)
        echo "Invalid choice. Please select 1, 2, 3, or 4."
        ;;
esac


