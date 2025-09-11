window.app = Vue.createApp({
  el: '#vue',
  mixins: [windowMixin],
  delimiters: ['${', '}'],
  data() {
    return {
      settings: {
        id: null,
        cost: 0,
        wallet: null,
        comment_word_limit: 50,
        tags: []
      },
      savingSettings: false,

      // tag + list
      selectedTag: null,
      allReviews: [],

      // stats from API
      avgRatingRaw: 0,
      reviewCount: 0,

      // pagination
      limit: 10,
      nextCursor: null,
      cursorStack: [null],
      paidReviewsLoading: false
    }
  },
  computed: {
    canGoBack() {
      return this.cursorStack.length > 1
    },
    // one decimal place like public page
    avgRating() {
      const v = Math.round(this.avgRatingRaw) / 2 / 100
      // snap to nearest 0.5
      const snapped = Math.round(v * 2) / 2
      return snapped
    }
  },
  methods: {
    shortWallet(id) {
      if (!id) return ''
      return id.length <= 12 ? id : `${id.slice(0, 6)}…${id.slice(-4)}`
    },
    formatDate(iso) {
      if (!iso) return ''
      try {
        return new Date(iso).toLocaleString()
      } catch {
        return iso
      }
    },
    async getSettings() {
      this.settings = await LNbits.api
        .request(
          'GET',
          '/paidreviews/api/v1/settings',
          this.g.user.wallets[0].adminkey
        )
        .then(r => r.data)
        .catch(() => this.settings)
    },
    async saveSettings() {
      this.savingSettings = true
      try {
        if (!this.settings.id) {
          this.settings = await LNbits.api
            .request(
              'POST',
              '/paidreviews/api/v1/settings',
              this.g.user.wallets[0].adminkey,
              this.settings
            )
            .then(r => r.data)
        } else {
          this.settings = await LNbits.api
            .request(
              'PUT',
              `/paidreviews/api/v1/settings/${encodeURIComponent(this.settings.id)}`,
              this.g.user.wallets[0].adminkey,
              this.settings
            )
            .then(r => r.data)
        }
      } finally {
        this.$q.notify({
          type: 'positive',
          message: 'Settings saved successfully',
          position: 'bottom'
        })
        this.savingSettings = false
      }
    },
    async deleteReview(id) {
      try {
        await LNbits.api.request(
          'DELETE',
          `/paidreviews/api/v1/review/${encodeURIComponent(id)}`,
          this.g.user.wallets[0].adminkey
        )

        // Optimistically remove from current page
        const beforeCount = this.allReviews.length
        this.allReviews = this.allReviews.filter(r => r.id !== id)

        // Optionally nudge counters locally (server will correct on refetch)
        if (beforeCount !== this.allReviews.length && this.reviewCount > 0) {
          this.reviewCount -= 1
        }

        // Refresh the same page cursor + stats from server
        await this.fetchPage({
          before: this.cursorStack[this.cursorStack.length - 1] ?? null,
          reset: true
        })
      } catch (e) {
        console.error(e)
        this.$q.notify({
          type: 'negative',
          message: 'Delete failed',
          position: 'bottom'
        })
      }
    },
    resetAndLoad() {
      this.cursorStack = [null]
      this.fetchPage({before: null, reset: true})
    },
    async fetchPage({before = null, reset = false} = {}) {
      if (!this.settings.id || !this.selectedTag) {
        this.allReviews = []
        this.avgRatingRaw = 0
        this.reviewCount = 0
        this.nextCursor = null
        return
      }

      this.paidReviewsLoading = true
      try {
        const params = new URLSearchParams({limit: String(this.limit)})

        if (before !== null && before !== undefined) {
          params.set('before', String(before))
        }

        // Cache buster so we don’t get stale lists after DELETE
        params.set(
          '_',
          typeof crypto !== 'undefined' && crypto.randomUUID
            ? crypto.randomUUID()
            : String(Date.now())
        )

        const url =
          `/paidreviews/api/v1/${encodeURIComponent(this.settings.id)}/${encodeURIComponent(this.selectedTag)}?` +
          params.toString()

        const data = await LNbits.api
          .request('GET', url, this.g.user.wallets[0].adminkey)
          .then(r => r.data)

        this.allReviews = data.items || []
        this.nextCursor = data.next_cursor || null
        this.avgRatingRaw = Number(data.avg_rating || 0)
        this.reviewCount = Number(data.review_count || 0)

        if (reset) {
          // keep the current page’s cursor at the top of the stack
          this.cursorStack = [before ?? null]
        } else if (before !== null && before !== undefined) {
          this.cursorStack.push(before)
        }
      } catch (e) {
        console.error(e)
        this.allReviews = []
        this.nextCursor = null
      } finally {
        this.paidReviewsLoading = false
      }
    },
    async goNext() {
      if (!this.nextCursor) return
      await this.fetchPage({before: this.nextCursor, reset: false})
    },
    async goBack() {
      if (!this.canGoBack) return
      this.cursorStack.pop()
      const prev = this.cursorStack[this.cursorStack.length - 1] ?? null
      await this.fetchPage({before: prev, reset: true})
    },
    fixRating(rating) {
      return Math.round((rating / 2 / 100) * 2) / 2
    }
  },
  async mounted() {
    await this.getSettings()
    this.selectedTag = this.settings.tags?.[0] || null
    await this.fetchPage({before: null, reset: true})
  }
})
