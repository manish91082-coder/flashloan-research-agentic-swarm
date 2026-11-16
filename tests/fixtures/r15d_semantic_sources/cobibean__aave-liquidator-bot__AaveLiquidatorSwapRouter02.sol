// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20Minimal {
    function balanceOf(address account) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
}

interface IAavePoolMinimal {
    function flashLoanSimple(address receiverAddress, address asset, uint256 amount, bytes calldata params, uint16 referralCode) external;
    function liquidationCall(address collateralAsset, address debtAsset, address user, uint256 debtToCover, bool receiveAToken) external;
}

interface ISwapRouter02Minimal {
    struct ExactInputSingleParams {
        address tokenIn;
        address tokenOut;
        uint24 fee;
        address recipient;
        uint256 amountIn;
        uint256 amountOutMinimum;
        uint160 sqrtPriceLimitX96;
    }
    function factory() external view returns (address);
    function WETH9() external view returns (address);
    function exactInputSingle(ExactInputSingleParams calldata params) external payable returns (uint256 amountOut);
    struct ExactInputParams { bytes path; address recipient; uint256 amountIn; uint256 amountOutMinimum; }
    function exactInput(ExactInputParams calldata params) external payable returns (uint256 amountOut);
}

interface IUniswapV3FactoryMinimal {
    function getPool(address tokenA, address tokenB, uint24 fee) external view returns (address);
}

contract AaveLiquidatorSwapRouter02 {
    IAavePoolMinimal public immutable aavePool;
    IAavePoolMinimal public immutable POOL;
    ISwapRouter02Minimal public immutable netSwapRouter;
    address public owner;
    uint256 public slippageTolerance = 0;

    uint256 public minProfit = 0;

    uint24[] private commonFeeTiers;
    address[] private intermediateTokens;
    mapping(address => mapping(address => uint24)) public preferredFeeTier;

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event PreferredFeeTierSet(address indexed tokenIn, address indexed tokenOut, uint24 fee);
    event CommonFeeTiersSet(uint24[] feeTiers);
    event IntermediateTokensSet(address[] tokens);
    event MinProfitSet(uint256 minProfit);
    event LiquidationProfit(address indexed user, address indexed debtAsset, uint256 amountOwed, uint256 finalBalance);

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    constructor(address _aavePool, address _swapRouter02) {
        require(_aavePool != address(0), "pool is zero");
        require(_swapRouter02 != address(0), "router is zero");
        owner = msg.sender;
        aavePool = IAavePoolMinimal(_aavePool);
        POOL = IAavePoolMinimal(_aavePool);
        netSwapRouter = ISwapRouter02Minimal(_swapRouter02);
    }

    function setMinProfit(uint256 _minProfit) external onlyOwner {
        minProfit = _minProfit;
        emit MinProfitSet(_minProfit);
    }

    function triggerLiquidation(address debtAsset, uint256 debtAmount, address targetUser, address collateralAsset) external onlyOwner {
        _triggerLiquidation(debtAsset, debtAmount, targetUser, collateralAsset, minProfit, "");
    }

    function triggerLiquidationWithMinProfit(address debtAsset, uint256 debtAmount, address targetUser, address collateralAsset, uint256 minProfitForCall) external onlyOwner {
        uint256 floor = minProfitForCall > minProfit ? minProfitForCall : minProfit;
        _triggerLiquidation(debtAsset, debtAmount, targetUser, collateralAsset, floor, "");
    }

    function triggerLiquidationWithPath(address debtAsset, uint256 debtAmount, address targetUser, address collateralAsset, uint256 minProfitForCall, bytes calldata swapPath) external onlyOwner {
        uint256 floor = minProfitForCall > minProfit ? minProfitForCall : minProfit;
        _triggerLiquidation(debtAsset, debtAmount, targetUser, collateralAsset, floor, swapPath);
    }

    function _triggerLiquidation(address debtAsset, uint256 debtAmount, address targetUser, address collateralAsset, uint256 floor, bytes memory swapPath) internal {
        require(debtAsset != address(0), "debt is zero");
        require(collateralAsset != address(0), "collateral is zero");
        require(targetUser != address(0), "user is zero");
        require(debtAmount > 0, "debt amount is zero");
        bytes memory params = abi.encode(targetUser, collateralAsset, floor, swapPath);
        aavePool.flashLoanSimple(address(this), debtAsset, debtAmount, params, 0);
    }

    function executeOperation(
        address debtAsset,
        uint256 debtAmount,
        uint256 premium,
        address initiator,
        bytes calldata params
    ) external returns (bool) {
        require(msg.sender == address(aavePool), "caller is not pool");
        require(initiator == address(this), "bad initiator");

        (address targetUser, address collateralAsset, uint256 floor, bytes memory swapPath) =
            abi.decode(params, (address, address, uint256, bytes));
        _safeApprove(debtAsset, address(aavePool), debtAmount);
        aavePool.liquidationCall(collateralAsset, debtAsset, targetUser, debtAmount, false);

        uint256 amountOwed = debtAmount + premium;
        uint256 requiredBalance = amountOwed + floor;
        uint256 debtBalance = IERC20Minimal(debtAsset).balanceOf(address(this));

        if (debtBalance < requiredBalance && collateralAsset != debtAsset) {
            uint256 collateralBalance = IERC20Minimal(collateralAsset).balanceOf(address(this));
            require(collateralBalance > 0, "no collateral received");
            _safeApprove(collateralAsset, address(netSwapRouter), collateralBalance);
            bytes memory path = swapPath.length > 0 ? swapPath : _resolveSwapPath(collateralAsset, debtAsset);
            netSwapRouter.exactInput(ISwapRouter02Minimal.ExactInputParams({
                path: path, recipient: address(this), amountIn: collateralBalance,
                amountOutMinimum: requiredBalance - debtBalance
            }));
            debtBalance = IERC20Minimal(debtAsset).balanceOf(address(this));
        }

        require(debtBalance >= requiredBalance, "profit floor not met");
        emit LiquidationProfit(targetUser, debtAsset, amountOwed, debtBalance);
        _safeApprove(debtAsset, address(aavePool), amountOwed);
        return true;
    }

    function _safeApprove(address token, address spender, uint256 amount) internal {}
    function _resolveSwapPath(address tokenIn, address tokenOut) internal view returns (bytes memory) {}
}
