/**
 * Formats a number with commas (e.g., 1000 -> 1,000)
 * @param num - The number to format
 * @returns The formatted string
 */
export function formatNumber(num: number): string {
  if (num === undefined || num === null) return '0';
  return num.toLocaleString();
}

/**
 * Formats a number as currency
 * @param amount - The numeric amount
 * @param currency - The currency code (default: USD)
 * @returns The formatted currency string
 */
export function formatCurrency(amount: number, currency: string = 'USD'): string {
  if (amount === undefined || amount === null) return '$0.00';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
  }).format(amount);
}

/**
 * Formats an ISO date string to a human-readable format
 * @param dateString - The ISO date string
 * @returns Formatted date like "Oct 15, 2023"
 */
export function formatDate(dateString: string): string {
  if (!dateString) return '';
  return new Date(dateString).toLocaleDateString(undefined, { 
    month: 'short', 
    day: 'numeric',
    year: 'numeric'
  });
}
