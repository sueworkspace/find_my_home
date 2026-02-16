import './LoadingSpinner.css';

export default function LoadingSpinner() {
  return (
    <div className="loading-spinner">
      <div className="loading-spinner__ring">
        <div></div>
        <div></div>
        <div></div>
        <div></div>
      </div>
      <p className="loading-spinner__text">매물 정보를 불러오는 중...</p>
    </div>
  );
}
