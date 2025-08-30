import { computed } from 'vue';
import { filteredTrades, amountCase } from '../stores/globals.js';
import { useXDecFormat } from './utils.js';

export function useReturnAnalysis() {
    const returnStats = computed(() => {
        let tradeCount = 0;
        let winnerCount = 0;
        let loserCount = 0;
        
        // For cost-weighted total return
        let totalProceeds = 0;
        let totalCost = 0;

        // For cost-weighted winner/loser returns
        let totalWinnerProceeds = 0;
        let totalWinnerCost = 0;
        let totalLoserProceeds = 0;
        let totalLoserCost = 0;

        if (filteredTrades && filteredTrades.length > 0) {
            filteredTrades.forEach(day => {
                if (day && day.trades) {
                    day.trades.forEach(trade => {
                        const cost = trade.buyQuantity * trade.entryPrice;
                        if (cost && cost !== 0) {
                            const proceeds = trade[amountCase.value + 'Proceeds'];
                            
                            tradeCount++;
                            
                            // Accumulate for cost-weighted total return
                            totalProceeds += proceeds;
                            totalCost += cost;

                            if (proceeds > 0) {
                                // Accumulate for cost-weighted winner return
                                totalWinnerProceeds += proceeds;
                                totalWinnerCost += cost;
                                winnerCount++;
                            } else if (proceeds < 0) {
                                // Accumulate for cost-weighted loser return
                                totalLoserProceeds += proceeds;
                                totalLoserCost += cost;
                                loserCount++;
                            }
                        }
                    });
                }
            });
        }

        const avgReturn = totalCost > 0 ? (totalProceeds / totalCost) * 100 : 0;
        const totalReturn = totalCost > 0 ? (totalProceeds / totalCost) * 100 : 0;
        const avgWinnerReturn = totalWinnerCost > 0 ? (totalWinnerProceeds / totalWinnerCost) * 100 : 0;
        const avgLoserReturn = totalLoserCost > 0 ? (totalLoserProceeds / totalLoserCost) * 100 : 0;

        return {
            avgReturn: `${useXDecFormat(avgReturn, 2)}%`,
            totalReturn: `${useXDecFormat(totalReturn, 2)}%`,
            avgWinnerReturn: `${useXDecFormat(avgWinnerReturn, 2)}%`,
            avgLoserReturn: `${useXDecFormat(avgLoserReturn, 2)}%`,
            hasTrades: tradeCount > 0
        };
    });
    return { returnStats };
} 