/**
 * 서버 인스턴스가 뜰 때 한 번 실행된다.
 *
 * 캐시 무효화 통지를 Redis 구독으로 받는다. 백엔드가 HTTP 로 한 곳만 때리면
 * 인스턴스를 여러 대 띄웠을 때 그 한 대만 갱신되고 나머지는 낡은 글을 계속 내보낸다.
 * 구독은 인스턴스마다 각자 하므로 몇 대든 전부 깨진다.
 */
export async function register() {
  // Edge 런타임에는 TCP 소켓이 없다. Node 프로세스에서만 붙인다.
  if (process.env.NEXT_RUNTIME !== 'nodejs') return
  if (!process.env.REDIS_URL) return

  /*
   * webpackIgnore — 번들링하지 말고 런타임에 Node 가 직접 불러오게 한다.
   *
   * Next 는 instrumentation.ts 를 edge 런타임용으로도 컴파일한다. edge 에는
   * net/dns/tls 가 없어서, 위 가드 때문에 실행되지 않더라도 '번들에 넣으려는 시도'
   * 만으로 빌드가 깨진다.
   */
  const { default: Redis } = await import(/* webpackIgnore: true */ 'ioredis')
  const channel = 'devshiplog:revalidate'
  const self = `http://127.0.0.1:${process.env.PORT || 3000}/api/revalidate`
  const secret = process.env.REVALIDATE_SECRET || ''

  const sub = new Redis(process.env.REDIS_URL, {
    // Redis 가 죽어도 앱은 계속 서비스해야 한다. 무한 재시도를 걸되 간격을 벌린다.
    retryStrategy: (attempt) => Math.min(attempt * 1000, 30_000),
    maxRetriesPerRequest: null,
    lazyConnect: false,
  })

  sub.on('error', (err) => {
    // 연결 실패는 경고로만. 시간 기반 재검증이 결국 따라잡는다.
    console.warn('[revalidate] Redis 구독 오류:', err.message)
  })

  sub.on('message', (_channel, payload) => {
    /*
     * revalidateTag 를 여기서 직접 부르지 않는다. Next 는 요청 컨텍스트 밖에서의
     * 호출을 보장하지 않는다. 자기 자신의 라우트 핸들러를 거치면 확실하다.
     */
    void fetch(self, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Revalidate-Secret': secret },
      body: payload,
    }).catch((err) => console.warn('[revalidate] 적용 실패:', err?.message))
  })

  await sub.subscribe(channel)
  console.log(`[revalidate] ${channel} 구독 시작`)
}
