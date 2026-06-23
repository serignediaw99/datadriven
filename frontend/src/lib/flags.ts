export const FLAGS: Record<string, string> = {
  "Algeria": "🇩🇿", "Argentina": "🇦🇷", "Australia": "🇦🇺",
  "Austria": "🇦🇹", "Belgium": "🇧🇪", "Bosnia & Herzegovina": "🇧🇦",
  "Brazil": "🇧🇷", "Canada": "🇨🇦", "Cape Verde": "🇨🇻",
  "Colombia": "🇨🇴", "Croatia": "🇭🇷", "Curaçao": "🇨🇼",
  "Czech Republic": "🇨🇿", "DR Congo": "🇨🇩", "Ecuador": "🇪🇨",
  "Egypt": "🇪🇬", "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "France": "🇫🇷",
  "Germany": "🇩🇪", "Ghana": "🇬🇭", "Haiti": "🇭🇹",
  "Iran": "🇮🇷", "Iraq": "🇮🇶", "Ivory Coast": "🇨🇮",
  "Japan": "🇯🇵", "Jordan": "🇯🇴", "Mexico": "🇲🇽",
  "Morocco": "🇲🇦", "Netherlands": "🇳🇱", "New Zealand": "🇳🇿",
  "Norway": "🇳🇴", "Panama": "🇵🇦", "Paraguay": "🇵🇾",
  "Portugal": "🇵🇹", "Qatar": "🇶🇦", "Saudi Arabia": "🇸🇦",
  "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "Senegal": "🇸🇳", "South Africa": "🇿🇦",
  "South Korea": "🇰🇷", "Spain": "🇪🇸", "Sweden": "🇸🇪",
  "Switzerland": "🇨🇭", "Tunisia": "🇹🇳", "Turkey": "🇹🇷",
  "USA": "🇺🇸", "Uruguay": "🇺🇾", "Uzbekistan": "🇺🇿",
}

export const flag = (team: string) => FLAGS[team] ?? '🏳️'
