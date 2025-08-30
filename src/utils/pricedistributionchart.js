<template>
  <div class="chart-container" ref="chartContainer"></div>
</template>

<script>
import * as d3 from 'd3'

export default {
  name: 'PriceDistributionChart',
  data() {
    return {
        <>
      // demo data: 1000 samples from N(50,10)
      prices: Array.from({ length: 1000 }, () => {
        let u = 0, v = 0
        while (u === 0) u = Math.random()
        while (v === 0) v = Math.random()
        const stdn = Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v)
        return 50 + 10 * stdn
      }),
      binSize: 5,
      width: 800,
      height: 400,
      smoothingWindow: 3
    }
  },
  mounted() {
    this.drawChart()
  },
  methods: {
    drawChart() {
      const prices = this.prices
      const { binSize, width, height, smoothingWindow } = this

      // 1. bin the data
      const minP = d3.min(prices)
      const maxP = d3.max(prices)
      const binCount = Math.ceil((maxP - minP) / binSize)
      const bins = d3.bin()
        .domain([minP, minP + binCount * binSize])
        .thresholds(binCount)
        (prices)

      // 2. % per bin
      const total = prices.length
      const pct = bins.map(b => (b.length / total) * 100)

      // 3. smooth via moving avg
      const smooth = pct.map((_, i, arr) => {
        const start = Math.max(0, i - Math.floor(smoothingWindow/2))
        const end   = Math.min(arr.length, i + Math.ceil(smoothingWindow/2))
        return d3.mean(arr.slice(start, end))
      })

      // 4. scales & margins
      const margin = { top: 20, right: 30, bottom: 40, left: 50 }
      const innerW = width - margin.left - margin.right
      const innerH = height - margin.top - margin.bottom

      const xScale = d3.scaleLinear()
        .domain([minP, minP + binCount * binSize])
        .range([0, innerW])

      const yScale = d3.scaleLinear()
        .domain([0, d3.max(smooth)]).nice()
        .range([innerH, 0])

      // 5. svg & group
      const svg = d3.select(this.$refs.chartContainer)
        .append('svg')
          .attr('width', width)
          .attr('height', height)

      const g = svg.append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`)

      // 6. axes
      g.append('g')
        .attr('transform', `translate(0,${innerH})`)
        .call(d3.axisBottom(xScale))
        .append('text')
          .attr('x', innerW / 2)
          .attr('y', 35)
          .attr('fill', '#000')
          .text('Price')

      g.append('g')
        .call(d3.axisLeft(yScale))
        .append('text')
          .attr('transform', 'rotate(-90)')
          .attr('x', -innerH / 2)
          .attr('y', -40)
          .attr('fill', '#000')
          .text('Probability (%)')

      // 7. area generator
      const areaGen = d3.area()
        .x((d,i) => xScale(minP + (i + 0.5) * binSize))
        .y0(innerH)
        .y1(d => yScale(d))
        .curve(d3.curveMonotoneX)

      // 8. draw area
      g.append('path')
        .datum(smooth)
        .attr('fill', 'steelblue')
        .attr('opacity', 0.6)
        .attr('d', areaGen)
    }
  }
}
</script>

<style scoped>
.chart-container {
  background: #fafafa;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
}
svg {
  font-family: sans-serif;
  font-size: 12px;
}
</style>
