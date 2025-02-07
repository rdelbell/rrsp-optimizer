import yaml
import matplotlib.pyplot as plt
import numpy as np
from tabulate import tabulate

def load_config(config_path="config.yaml"):
    """Loads configuration from a YAML file."""
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    def process_brackets(brackets):
        """Converts 'null' upper bounds to infinity."""
        return [(lower, float('inf') if upper is None else upper, rate) for lower, upper, rate in brackets]

    default_inputs = config.get("default_inputs", {})
    federal_brackets = process_brackets(config.get("federal_brackets", []))
    quebec_brackets = process_brackets(config.get("quebec_brackets", []))
    
    return default_inputs, federal_brackets, quebec_brackets

def compute_tax(income, brackets):
    """Computes the base tax liability based on income and provided tax brackets."""
    tax = 0.0
    for lower, upper, rate in brackets:
        if income > lower:
            taxable_in_bracket = min(income, upper) - lower
            tax += taxable_in_bracket * rate
        else:
            break
    return tax

def compute_total_tax_liability(taxable_income, is_quebec, medical_expenses, federal_brackets, quebec_brackets):
    """Computes total tax liability considering medical expense credits for federal and Quebec taxes."""
    def medical_expense_credit(income, expenses, threshold, rate):
        eligible_med = max(0, expenses - min(threshold * income, threshold))
        return eligible_med * rate

    federal_tax = compute_tax(taxable_income, federal_brackets)
    federal_tax -= medical_expense_credit(taxable_income, medical_expenses, 2479, 0.15)
    
    if is_quebec:
        quebec_tax = compute_tax(taxable_income, quebec_brackets)
        quebec_tax -= medical_expense_credit(taxable_income, medical_expenses, 1600, 0.20)
        return max(0, federal_tax) + max(0, quebec_tax)
    
    return max(0, federal_tax)

def find_rrsp_contribution_for_net_zero(income, investment_profits, taxes_paid, medical_expenses, is_quebec,
                                        federal_brackets, quebec_brackets, rrsp_room):
    """Finds the minimal RRSP contribution to achieve a net balance of zero."""
    taxable_income = income + investment_profits
    def net_balance(c):
        return compute_total_tax_liability(taxable_income - c, is_quebec, medical_expenses, federal_brackets, quebec_brackets) - taxes_paid

    if net_balance(0) <= 0:
        return 0.0
    if net_balance(rrsp_room) > 0:
        return None

    low, high, tolerance = 0.0, rrsp_room, 1.0
    while high - low > tolerance:
        mid = (low + high) / 2
        if abs(net_balance(mid)) < tolerance:
            return mid
        elif net_balance(mid) > 0:
            low = mid
        else:
            high = mid
    return high

def generate_contribution_table_pretty(income, investment_profits, rrsp_room, medical_expenses, is_quebec,
                                       federal_brackets, quebec_brackets, taxes_paid):
    """Generates a nicely formatted table showing the effect of different RRSP contributions."""
    taxable_income = income + investment_profits
    base_tax = compute_total_tax_liability(taxable_income, is_quebec, medical_expenses, federal_brackets, quebec_brackets)
    
    table_rows = []
    headers = ["Contribution", "Taxable Income", "Total Tax Liability", "Tax Savings", "Net Balance"]
    
    for c in np.linspace(0, rrsp_room, 20):
        new_taxable = taxable_income - c
        new_tax = compute_total_tax_liability(new_taxable, is_quebec, medical_expenses, federal_brackets, quebec_brackets)
        savings = base_tax - new_tax
        net_balance = new_tax - taxes_paid
        table_rows.append([f"${c:,.2f}", f"${new_taxable:,.2f}", f"${new_tax:,.2f}", f"${savings:,.2f}", f"${net_balance:,.2f}"])

    print("\n--- RRSP Contribution Analysis ---")
    print(tabulate(table_rows, headers=headers, tablefmt="markdown"))

def plot_net_balance_curve(income, investment_profits, rrsp_room, medical_expenses, is_quebec,
                           federal_brackets, quebec_brackets, taxes_paid):
    """Plots RRSP contribution vs. net balance and highlights the optimal contribution."""
    taxable_income = income + investment_profits
    contributions = np.linspace(0, rrsp_room, 100)
    net_balances = [compute_total_tax_liability(taxable_income - c, is_quebec, medical_expenses, federal_brackets, quebec_brackets) - taxes_paid for c in contributions]
    
    sweet_spot_idx = np.abs(net_balances).argmin()
    sweet_contribution, sweet_net_balance = contributions[sweet_spot_idx], net_balances[sweet_spot_idx]

    plt.figure(figsize=(10, 6))
    plt.scatter(sweet_contribution, sweet_net_balance, color="red", label=f"Sweet Spot (${sweet_contribution:,.2f})")
    plt.plot(contributions, net_balances, color="blue", marker="o", markersize=4, alpha=0.7, label="Net Balance")
    plt.axhline(0, color="black", linestyle="--")
    
    plt.xlabel("RRSP Contribution")
    plt.ylabel("Net Balance (Tax Liability - Taxes Paid)")
    plt.title("Net Balance vs. RRSP Contribution")
    plt.legend()
    plt.grid(True)
    plt.show()

def main():
    default_inputs, federal_brackets, quebec_brackets = load_config("config.yaml")
    income, taxes_paid, investment_profits, rrsp_room, medical_expenses, is_quebec = (
        default_inputs.get(k) for k in ["income", "taxes_paid", "investment_profits", "rrsp_room", "medical_expenses", "is_quebec"]
    )

    generate_contribution_table_pretty(income, investment_profits, rrsp_room, medical_expenses, is_quebec, federal_brackets, quebec_brackets, taxes_paid)
    
    rrsp_for_net_zero = find_rrsp_contribution_for_net_zero(income, investment_profits, taxes_paid, medical_expenses, is_quebec, federal_brackets, quebec_brackets, rrsp_room)
    print(f"\nOptimal RRSP Contribution for Net Balance Zero: ${rrsp_for_net_zero:,.2f}" if rrsp_for_net_zero else "Zero balance not achievable.")
    
    plot_net_balance_curve(income, investment_profits, rrsp_room, medical_expenses, is_quebec, federal_brackets, quebec_brackets, taxes_paid)

if __name__ == "__main__":
    main()
