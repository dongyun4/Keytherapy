// 파일 경로: /api/getSentences.js

// 이 함수는 Vercel에 의해 서버리스 함수로 자동 변환됩니다.
// export default 키워드가 필수입니다.
export default function handler(request, response) {
  
  // 실제로는 DB나 다른 곳에서 데이터를 가져오겠지만, 여기서는 예시로 객체를 사용합니다.
  const sentencePool = {
    kor: ["서버에서 가져온 새로운 한글 문장입니다.", "백엔드 API 테스트 문장입니다."],
    eng: ["This sentence is from the server.", "This is a backend API test sentence."]
  };

  // 클라이언트가 요청한 언어(예: ?lang=kor)를 확인합니다.
  const lang = request.query.lang || 'kor';
  
  const sentences = sentencePool[lang] || sentencePool['kor'];
  const randomSentence = sentences[Math.floor(Math.random() * sentences.length)];

  // 클라이언트에 JSON 형태로 응답을 보냅니다.
  response.status(200).json({
    sentence: randomSentence,
  });
}