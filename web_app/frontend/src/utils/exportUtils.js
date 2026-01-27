/**
 * Export utilities for downloading product data
 */

export const exportToCSV = (products, keyword) => {
    const headers = [
        'Rank', 'Title', 'ASIN', 'Price', 'Est. Revenue', 'Est. Sales', 
        'Margin %', 'Profit/Unit', 'Score', 'Rating', 'Reviews', 'BSR',
        'Market Share %', 'Brand Risk', 'Hazmat', 'Vetoed'
    ]
    
    const rows = products.map((p, idx) => [
        idx + 1,
        `"${p.title?.replace(/"/g, '""')}"`,
        p.asin,
        p.price?.toFixed(2),
        p.est_revenue?.toFixed(0),
        Math.round(p.estimated_sales),
        p.margin?.toFixed(1),
        p.est_profit?.toFixed(2),
        p.enhanced_score,
        p.rating,
        p.reviews,
        p.bsr,
        p.market_share?.toFixed(2),
        p.risks?.brand_risk || 'N/A',
        p.risks?.hazmat ? 'YES' : 'NO',
        p.is_vetoed ? 'YES' : 'NO'
    ])
    
    const csv = [headers, ...rows].map(row => row.join(',')).join('\n')
    downloadFile(csv, `amazon-hunter-${keyword}-${Date.now()}.csv`, 'text/csv')
}

export const exportToJSON = (products, keyword, summary) => {
    const data = {
        exported_at: new Date().toISOString(),
        keyword,
        summary,
        products
    }
    const json = JSON.stringify(data, null, 2)
    downloadFile(json, `amazon-hunter-${keyword}-${Date.now()}.json`, 'application/json')
}

const downloadFile = (content, filename, mimeType) => {
    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
}
