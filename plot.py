import matplotlib.pyplot as plt
import numpy as np

# Generate concentration data (0 to 100%)
concentration = np.linspace(0, 100, 200)

# Define sigmoid function for dose-response curves
def sigmoid(x, max_response, ec50=50, hill_slope=0.1):
    """
    Sigmoid function for dose-response curves
    x: concentration/dose
    max_response: maximum response (efficacy)
    ec50: concentration at 50% of max response
    hill_slope: steepness of the curve
    """
    return max_response / (1 + np.exp(-(x - ec50) / (1/hill_slope)))

# Generate response curves for different agonist types
full_agonist = sigmoid(concentration, max_response=100)      # 100% efficacy
partial_agonist = sigmoid(concentration, max_response=45)    # 45% efficacy
inverse_agonist = sigmoid(concentration, max_response=-40)   # Negative response
baseline = np.zeros_like(concentration)                      # Baseline at 0

# Create the plot
plt.figure(figsize=(12, 8))

# Plot the curves
plt.plot(concentration, full_agonist, 'r-', linewidth=3, 
         label='Full Agonist (Morphine)', alpha=0.8)
plt.plot(concentration, partial_agonist, 'b-', linewidth=3, 
         label='Partial Agonist (Buprenorphine)', alpha=0.8)
plt.plot(concentration, inverse_agonist, color='purple', linewidth=3, 
         label='Inverse Agonist (Beta-carbolines)', alpha=0.8)
plt.plot(concentration, baseline, 'k--', linewidth=2, 
         label='Baseline', alpha=0.5)

# Add horizontal reference lines for max efficacy
plt.axhline(y=100, color='red', linestyle=':', alpha=0.3, linewidth=1)
plt.axhline(y=45, color='blue', linestyle=':', alpha=0.3, linewidth=1)
plt.axhline(y=0, color='gray', linestyle='-', alpha=0.5, linewidth=1.5)

# Add annotations
plt.annotate('100% Efficacy\n(Full Agonist)', 
             xy=(85, 100), xytext=(70, 105),
             fontsize=10, color='red', fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='red'))

plt.annotate('~45% Efficacy\n(Partial Agonist)\nCeiling Effect', 
             xy=(85, 45), xytext=(65, 60),
             fontsize=10, color='blue', fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='blue'),
             arrowprops=dict(arrowstyle='->', color='blue', lw=1.5))

plt.annotate('Inverse Activity\n(Below Baseline)', 
             xy=(85, -40), xytext=(60, -55),
             fontsize=10, color='purple', fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='purple'),
             arrowprops=dict(arrowstyle='->', color='purple', lw=1.5))

# Labels and title
plt.xlabel('Drug Concentration / Receptor Occupancy (%)', fontsize=14, fontweight='bold')
plt.ylabel('Biological Response (%)', fontsize=14, fontweight='bold')
plt.title('Drug-Receptor Interactions: Types of Agonists\nDose-Response Curves', 
          fontsize=16, fontweight='bold', pad=20)

# Legend
plt.legend(loc='upper left', fontsize=11, framealpha=0.9)

# Grid
plt.grid(True, alpha=0.3, linestyle='--')

# Set axis limits
plt.xlim(0, 100)
plt.ylim(-60, 115)

# Add text box with key information
textstr = '\n'.join([
    'Key Concepts:',
    '• Full Agonist: 100% maximal response',
    '• Partial Agonist: Submaximal response (~45%)',
    '  even at full receptor occupancy',
    '• Inverse Agonist: Reduces basal activity',
    '  producing opposite effects'
])
props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
plt.text(0.02, 0.35, textstr, transform=plt.gca().transAxes, 
         fontsize=10, verticalalignment='top', bbox=props)

# Tight layout for better spacing
plt.tight_layout()

# Save the plot to a file
plt.savefig('dose_response_plot.png', dpi=300, bbox_inches='tight')

# Display the plot (commented out for console run)
# plt.show()

# Optional: Print some data points for verification
print("Sample Data Points:")
print(f"{'Concentration':<15} {'Full Agonist':<15} {'Partial Agonist':<20} {'Inverse Agonist'}")
print("-" * 70)
for i in [0, 25, 50, 75, 100]:
    idx = int(i * 2)  # Since we have 200 points for 0-100 range
    print(f"{concentration[idx]:<15.1f} {full_agonist[idx]:<15.2f} "
          f"{partial_agonist[idx]:<20.2f} {inverse_agonist[idx]:.2f}")