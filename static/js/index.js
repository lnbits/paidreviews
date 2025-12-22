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
      paidReviewsLoading: false,
      reviews: [],
      reviewsTable: {
        loading: false,
        columns: [
          {
            name: 'actions',
            align: 'left',
            label: '',
            field: 'actions',
            sortable: false
          },
          {
            name: 'name',
            align: 'left',
            label: this.$t('Name'),
            field: 'name',
            sortable: true
          },

          {
            name: 'comment',
            align: 'left',
            label: this.$t('Comment'),
            field: 'comment'
          },
          {
            name: 'rating',
            align: 'right',
            label: 'Rating',
            field: 'rating'
          }
        ],
        pagination: {
          rowsPerPage: 10,
          sortBy: 'created_at',
          descending: true,
          page: 1
        }
      }
    }
  },
  computed: {
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
      this.$q
        .dialog({
          title: 'Confirm Delete',
          message: 'Are you sure you want to delete this review?',
          cancel: true,
          persistent: true
        })
        .onOk(async () => {
          try {
            await LNbits.api.request(
              'DELETE',
              `/paidreviews/api/v1/${this.settings.id}/reviews/${id}`
            )

            await this.getTagReviews()
          } catch (e) {
            console.error(e)
            this.$q.notify({
              type: 'negative',
              message: 'Delete failed',
              position: 'bottom'
            })
          }
        })
    },
    resetAndLoad() {
      this.getTagReviews()
    },

    async getTagReviews(props) {
      try {
        this.reviewsTable.loading = true
        const params = LNbits.utils.prepareFilterQuery(this.reviewsTable, props)
        const {data} = await LNbits.api.request(
          'GET',
          `/paidreviews/api/v1/${this.settings.id}/reviews/${this.selectedTag}?${params}`,
          null
        )
        this.reviews = data.data
        this.avgRatingRaw = data.avg_rating
        this.reviewsTable.pagination.rowsNumber = data.total
      } catch (e) {
        LNbits.utils.notifyApiError(e)
      } finally {
        this.reviewsTable.loading = false
      }
    },

    fixRating(rating) {
      return Math.round((rating / 2 / 100) * 2) / 2
    }
  },
  async created() {
    await this.getSettings()
    this.selectedTag = this.settings.tags?.[0] || null
    await this.getTagReviews()
  }
})
