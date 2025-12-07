import matplotlib.pyplot as plt
import numpy as np

# All buckets in order
buckets = [
    '<20', '20-39', '40-59', '60-79', '80-99', '100-119', '120-139', '140-159',
    '160-179', '180-199', '200-219', '220-239', '240-259', '260-279', '280-299',
    '300-319', '320-339', '340-359', '360-379', '380-399', '400-419', '420-439',
    '440-459', '460-479', '480-499', '500+'
]

# Your positions (negative for "No" short positions)
# No shares = short position (negative exposure)
positions = [
    0,      # <20
    -15,    # 20-39: 15 No @ 99.9¢
    0,      # 40-59
    0,      # 60-79
    0,      # 80-99
    0,      # 100-119
    0,      # 120-139
    0,      # 140-159
    0,      # 160-179
    0,      # 180-199 (future body)
    0,      # 200-219 (future body)
    0,      # 220-239
    0,      # 240-259
    0,      # 260-279
    0,      # 280-299
    0,      # 300-319
    0,      # 320-339
    0,      # 340-359
    0,      # 360-379
    -20,    # 380-399: 20 No @ 97.3¢
    0,      # 400-419
    -25,    # 420-439: 25 No @ 97.5¢
    0,      # 440-459
    0,      # 460-479
    -5,     # 480-499: 5 No @ 98.5¢
    -15     # 500+: 15 No @ 99¢
]

# Investment per bucket (for sizing)
investments = [
    0,      # <20
    14.99,  # 20-39
    0,      # 40-59
    0,      # 60-79
    0,      # 80-99
    0,      # 100-119
    0,      # 120-139
    0,      # 140-159
    0,      # 160-179
    0,      # 180-199
    0,      # 200-219
    0,      # 220-239
    0,      # 240-259
    0,      # 260-279
    0,      # 280-299
    0,      # 300-319
    0,      # 320-339
    0,      # 340-359
    0,      # 360-379
    19.46,  # 380-399
    0,      # 400-419
    24.38,  # 420-439
    0,      # 440-459
    0,      # 460-479
    4.93,   # 480-499
    14.85   # 500+
]

# Create figure
fig, ax = plt.subplots(figsize=(16, 8))

# Color bars based on position type
colors = []
for pos in positions:
    if pos < 0:
        colors.append('#ff3860')  # Red for shorts (wings)
    elif pos > 0:
        colors.append('#00ff88')  # Green for longs (body)
    else:
        colors.append('#333333')  # Dark gray for empty

# Create bar chart
bars = ax.bar(buckets, positions, color=colors, edgecolor='white', linewidth=1.5, alpha=0.8)

# Add investment labels on bars
for i, (bar, inv) in enumerate(zip(bars, investments)):
    if inv > 0:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height - 2,
                f'${inv:.0f}',
                ha='center', va='top', fontsize=9, fontweight='bold', color='white')

# Styling
ax.axhline(y=0, color='white', linestyle='-', linewidth=2, alpha=0.3)
ax.set_xlabel('Tweet Count Buckets', fontsize=14, fontweight='bold')
ax.set_ylabel('Net Exposure (Shares)', fontsize=14, fontweight='bold')
ax.set_title('Your Butterfly Wings Strategy - Phase 1 Complete\nTotal Invested: $78.61', 
             fontsize=16, fontweight='bold', pad=20)
ax.grid(axis='y', alpha=0.3, linestyle='--')
ax.set_facecolor('#1a1a2e')
fig.patch.set_facecolor('#16213e')

# Rotate x-axis labels
plt.xticks(rotation=45, ha='right')

# Add legend
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='#ff3860', label='Wings (Short "No")'),
    Patch(facecolor='#00ff88', label='Body (Long "Yes") - Coming Soon'),
    Patch(facecolor='#333333', label='No Position')
]
ax.legend(handles=legend_elements, loc='upper left', fontsize=11)

# Add annotations
ax.text(0.5, 0.95, 'Phase 1: Wings Deployed ✅', 
        transform=ax.transAxes, fontsize=12, verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='green', alpha=0.3),
        ha='center')

ax.text(0.5, 0.05, 'Phase 3: Body (180-219) Coming Dec 13-15 ⏳', 
        transform=ax.transAxes, fontsize=12, verticalalignment='bottom',
        bbox=dict(boxstyle='round', facecolor='orange', alpha=0.3),
        ha='center')

plt.tight_layout()
plt.savefig('my_butterfly_wings.png', dpi=300, bbox_inches='tight', facecolor='#16213e')
print("✅ Chart saved as 'my_butterfly_wings.png'")
print("\nYour Wing Positions:")
print("=" * 50)
print(f"20-39:    {-positions[1]} shares @ 99.9¢ = ${investments[1]:.2f}")
print(f"380-399:  {-positions[19]} shares @ 97.3¢ = ${investments[19]:.2f}")
print(f"420-439:  {-positions[21]} shares @ 97.5¢ = ${investments[21]:.2f}")
print(f"480-499:  {-positions[24]} shares @ 98.5¢ = ${investments[24]:.2f}")
print(f"500+:     {-positions[25]} shares @ 99¢ = ${investments[25]:.2f}")
print("=" * 50)
print(f"Total Wings: ${sum(investments):.2f}")
print(f"Cash Remaining: ${250 - sum(investments):.2f}")
print("\n🦋 Butterfly Structure:")
print("   Low Wing (20-39): 1 position, $14.99")
print("   High Wings (380-500+): 4 positions, $63.62")
print("   Body (Coming): 180-219 range, ~$170")

plt.show()
