import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression

def get_linear_regression_prediction(target_hour):
    """Calculates the AI's prediction for the game based on the target hour."""
    return (target_hour * 4.5) + 12


def get_polynomial_regression_prediction(target_hour):
    """Placeholder for future implementation."""
    return (target_hour ** 2 * 0.5) + 10

def draw_ml_plot():
    """Generates the matplotlib figure for the game and visualizer."""
    np.random.seed(42)
    x = np.linspace(0, 10, 50)
    y = 4.5 * x + 12 + (np.random.randn(50) * 5)
    
    model = LinearRegression().fit(x.reshape(-1, 1), y)
    y_pred = model.predict(x.reshape(-1, 1))

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.scatter(x, y, color='blue', alpha=0.5, label='Historical Student Data')
    ax.plot(x, y_pred, color='red', linewidth=2, label='Regression Line')
    ax.set_xlabel("Study Hours")
    ax.set_ylabel("Marks")
    ax.legend()
    
    return fig